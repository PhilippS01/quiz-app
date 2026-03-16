#!/usr/bin/env python3

import os
import json
import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Sequence

import pandas as pd
import streamlit as st

# ------------------------------------------------------------------
# Ordner absolut relativ zur Datei app.py  (-> nie mehr extern!)
# ------------------------------------------------------------------
APP_DIR  = os.path.dirname(os.path.abspath(__file__))
QUIZ_DIR = os.path.join(APP_DIR, "quizzes")
RES_DIR  = os.path.join(APP_DIR, "results")

# Kompatibilität für alte Streamlit-Versionen
if not hasattr(st, "experimental_rerun"):
    st.experimental_rerun = st.rerun

# ------------------------------------------------------------------
# Datenmodell & Bewertung
# ------------------------------------------------------------------
@dataclass
class Question:
    prompt: str
    qtype: str          # "mc" | "open"
    correct: Sequence[str] | str
    options: Optional[Sequence[str]] = None
    weight: float = 1.0

def mc_grader(ans: str, corr: Sequence[str]) -> float:
    if not ans:                     # keine Antwort gegeben
        return 0.0
    
    u = {a.strip().lower() for a in ans.split("|") if a}  # Antworten des Users
    c = {c.strip().lower() for c in corr}                 # Korrekte Antworten

    if u - c:                       # enthält mindestens eine falsche Option
        return 0.0

    return len(u) / len(c) if c else 0.0

def open_grader(ans: str, corr: str) -> float:
    return float(ans.strip().lower() == str(corr).strip().lower())

# ------------------------------------------------------------------
# Fragen laden
# ------------------------------------------------------------------
def _df_to_questions(df: pd.DataFrame) -> List[Question]:
    qs: List[Question] = []
    for _, row in df.iterrows():
        qtype  = str(row["Typ"]).strip().lower()
        prompt = str(row["Frage"]).strip()
        weight = float(row.get("Gewicht", 1.0))
        corr   = str(row["Richtige Antworten"]).strip()
        if qtype == "mc":
            opts = [o.strip() for o in str(row["Antwortmöglichkeiten"]).split(";") if o.strip()]
            corr_list = [c.strip() for c in corr.split(";") if c.strip()]
            qs.append(Question(prompt, "mc", corr_list, opts, weight))
        else:
            qs.append(Question(prompt, "open", corr, None, weight))
    return qs

@st.cache_data(show_spinner=False)
def load_questions(file) -> List[Question]:
    ext = os.path.splitext(file.name)[1].lower()
    if ext in {".xls", ".xlsx"}:
        df = pd.read_excel(file)
    else:                         # CSV
        file.seek(0)
        df = pd.read_csv(file, sep=",", engine="python")
        if len(df.columns) == 1:  # evtl. Semikolon
            file.seek(0)
            df = pd.read_csv(file, sep=";", engine="python")
    df.columns = [c.strip() for c in df.columns]

    required = {"Frage", "Typ", "Antwortmöglichkeiten", "Richtige Antworten"}
    if not required.issubset(df.columns):
        missing = ", ".join(c for c in required if c not in df.columns)
        raise ValueError(f"Fehlende Spalten: {missing}")

    return _df_to_questions(df)

# ------------------------------------------------------------------
# Ergebnis anhängen
# ------------------------------------------------------------------
def save_result(name: str,
                answers: Dict[str, str],
                scores: Dict[str, float],
                questions: List[Question],
                quiz_id: str) -> None:
    row = {"Name": name,
           "Zeit": datetime.now().isoformat(timespec="seconds"),
           "Total": sum(scores.values())}
    for i, q in enumerate(questions, 1):
        row[f"F{i} Antwort"] = answers.get(q.prompt, "")
        row[f"F{i} Punkte"]  = round(scores.get(q.prompt, 0), 2)

    os.makedirs(RES_DIR, exist_ok=True)
    path = os.path.join(RES_DIR, f"{quiz_id}_results.csv")
    pd.DataFrame([row]).to_csv(path, mode="a", index=False,
                               header=not os.path.exists(path))

# ------------------------------------------------------------------
# Streamlit Config
# ------------------------------------------------------------------
st.set_page_config("Quiz", "❓", layout="centered")

# Query-Parameter vereinheitlichen
try:
    raw = st.query_params
    params = {k: v for k, v in raw.items()}
except AttributeError:
    raw = st.experimental_get_query_params()
    params = {k: v[0] if isinstance(v, list) else v for k, v in raw.items()}

# ================================================================
# QUIZ-MODUS
# ================================================================
if "quiz_id" in params:
    quiz_id = params["quiz_id"]
    qfile   = os.path.join(QUIZ_DIR, f"{quiz_id}_questions.csv")
    mfile   = os.path.join(QUIZ_DIR, f"{quiz_id}_meta.json")

    if not os.path.exists(qfile):
        st.error("Quiz nicht gefunden - Link korrekt?")
        st.stop()

    if not os.path.exists(mfile):
        st.error("Quiz-Metadaten nicht gefunden.")
        st.stop()

    with open(mfile, "r", encoding="utf-8") as f:
        meta = json.load(f)

    expires_at = datetime.fromisoformat(meta["expires_at"])
    if datetime.now() > expires_at:
        try:
            if os.path.exists(qfile):
                os.remove(qfile)
            if os.path.exists(mfile):
                os.remove(mfile)
        except Exception:
            pass

        st.error("Dieser Quiz-Link ist abgelaufen.")
        st.stop()

    with open(qfile, "rb") as f:
        questions = load_questions(f)

    st.title("📋 Online-Quiz")
    name = st.text_input("Dein Name")
    if name:
        st.divider()
        answers: Dict[str, str] = {}
        for i, q in enumerate(questions, 1):
            if q.qtype == "mc":
                sel = st.multiselect(f"{i}. {q.prompt}", q.options, key=f"q{i}")
                answers[q.prompt] = "|".join(sel)
            else:
                answers[q.prompt] = st.text_input(f"{i}. {q.prompt}", key=f"q{i}")

        if st.button("Antworten absenden", type="primary"):
            scores = {q.prompt: (q.weight * mc_grader(answers[q.prompt], q.correct)
                                 if q.qtype == "mc"
                                 else q.weight * open_grader(answers[q.prompt], q.correct))
                      for q in questions}
            save_result(name, answers, scores, questions, quiz_id)
            st.success("Danke, deine Antworten wurden eingereicht!")
            st.balloons()
            if st.button("Nächste Person"):
                for k in list(st.session_state.keys()):
                    if k.startswith("q") or k == "Name":
                        del st.session_state[k]
                st.experimental_rerun()

# ================================================================
# ADMIN-MODUS
# ================================================================
else:
    st.title("📋 Quiz-Administration")
    st.header("Quiz einrichten")

    up_file = st.file_uploader("Fragen-Datei (CSV / Excel)",
                               type=["csv", "xls", "xlsx"])

    if st.button("Quiz-Link erstellen"):
        if not up_file:
            st.error("Bitte erst eine Datei wählen.")
            st.stop()

        try:
            _ = load_questions(up_file)   # Validierung
        except Exception as e:
            st.error(f"Dateifehler: {e}")
            st.stop()

        quiz_id = str(uuid.uuid4())[:8]
        os.makedirs(QUIZ_DIR, exist_ok=True)

        qcsv = os.path.join(QUIZ_DIR, f"{quiz_id}_questions.csv")
        mfile = os.path.join(QUIZ_DIR, f"{quiz_id}_meta.json")

        up_file.seek(0)
        if up_file.name.lower().endswith((".xls", ".xlsx")):
            pd.read_excel(up_file).to_csv(qcsv, index=False)
        else:
            with open(qcsv, "wb") as f:
                f.write(up_file.read())

        created_at = datetime.now()
        expires_at = created_at + timedelta(days=7)

        meta = {
            "quiz_id": quiz_id,
            "created_at": created_at.isoformat(),
            "expires_at": expires_at.isoformat()
        }

        with open(mfile, "w", encoding="utf-8") as f:
            json.dump(meta, f, ensure_ascii=False, indent=2)

        st.success("Quiz erfolgreich angelegt! Link zum Teilen:")
        st.markdown(f"[➡️ Zum Quiz starten](/?quiz_id={quiz_id})")
        st.info(f"Link ist gültig bis: {expires_at.strftime('%d.%m.%Y %H:%M')}")
        st.code(quiz_id)

    # ----------------- Ergebnisse einsehen -----------------
    st.header("Quiz-Ergebnisse ansehen")
    quiz_to_check = st.text_input("Quiz-ID eingeben, um Ergebnisse zu laden:")
    if st.button("Ergebnisse laden") and quiz_to_check:
        res_file = os.path.join(RES_DIR, f"{quiz_to_check}_results.csv")
        if os.path.exists(res_file):
            df = pd.read_csv(res_file)
            st.write(f"Ergebnisse für Quiz {quiz_to_check}:")
            st.dataframe(df)
            st.download_button("CSV herunterladen",
                               df.to_csv(index=False).encode("utf-8"),
                               file_name=f"Quiz_{quiz_to_check}_Ergebnisse.csv")
        else:
            st.error("Keine Ergebnisse für diese Quiz-ID gefunden.")
