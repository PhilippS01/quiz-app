#!/usr/bin/env python3

import hashlib
import hmac
import io
import json
import uuid
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional, Sequence

import pandas as pd
import streamlit as st
from supabase import Client, create_client


QUIZ_VALID_DAYS = 7


@dataclass
class Question:
    prompt: str
    qtype: str  # "mc" | "open"
    correct: Sequence[str] | str
    options: Optional[Sequence[str]] = None
    weight: float = 1.0


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def parse_timestamp(value: str) -> datetime:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def mc_grader(answer: str, correct: Sequence[str]) -> float:
    if not answer:
        return 0.0

    selected = {item.strip().casefold() for item in answer.split("|") if item.strip()}
    expected = {str(item).strip().casefold() for item in correct if str(item).strip()}

    if not expected or selected - expected:
        return 0.0
    return len(selected) / len(expected)


def open_grader(answer: str, correct: str) -> float:
    return float(answer.strip().casefold() == str(correct).strip().casefold())


def _df_to_questions(df: pd.DataFrame) -> List[Question]:
    questions: List[Question] = []

    for row_number, (_, row) in enumerate(df.iterrows(), start=2):
        qtype = str(row["Typ"]).strip().lower()
        prompt = str(row["Frage"]).strip()
        correct_raw = str(row["Richtige Antworten"]).strip()

        if not prompt:
            raise ValueError(f"Zeile {row_number}: Die Frage ist leer.")
        if qtype not in {"mc", "open"}:
            raise ValueError(f"Zeile {row_number}: Typ muss 'mc' oder 'open' sein.")

        weight_raw = row.get("Gewicht", 1.0)
        weight = 1.0 if pd.isna(weight_raw) else float(weight_raw)
        if weight <= 0:
            raise ValueError(f"Zeile {row_number}: Gewicht muss größer als 0 sein.")

        if qtype == "mc":
            options_raw = row.get("Antwortmöglichkeiten", "")
            options = [item.strip() for item in str(options_raw).split(";") if item.strip()]
            correct = [item.strip() for item in correct_raw.split(";") if item.strip()]

            if len(options) < 2:
                raise ValueError(f"Zeile {row_number}: MC-Frage benötigt mindestens zwei Optionen.")
            if not correct:
                raise ValueError(f"Zeile {row_number}: Mindestens eine richtige Antwort fehlt.")

            option_lookup = {item.casefold() for item in options}
            invalid = [item for item in correct if item.casefold() not in option_lookup]
            if invalid:
                raise ValueError(
                    f"Zeile {row_number}: Richtige Antworten müssen als Antworttext angegeben werden. "
                    f"Nicht in den Optionen gefunden: {', '.join(invalid)}"
                )

            questions.append(Question(prompt, "mc", correct, options, weight))
        else:
            if not correct_raw:
                raise ValueError(f"Zeile {row_number}: Richtige Antwort fehlt.")
            questions.append(Question(prompt, "open", correct_raw, None, weight))

    if not questions:
        raise ValueError("Die Datei enthält keine Fragen.")
    return questions


def load_questions(uploaded_file) -> List[Question]:
    uploaded_file.seek(0)
    raw = uploaded_file.read()
    name = uploaded_file.name.lower()

    if name.endswith((".xls", ".xlsx")):
        df = pd.read_excel(io.BytesIO(raw))
    else:
        try:
            df = pd.read_csv(io.BytesIO(raw), sep=",", engine="python")
            if len(df.columns) == 1:
                df = pd.read_csv(io.BytesIO(raw), sep=";", engine="python")
        except UnicodeDecodeError:
            df = pd.read_csv(io.BytesIO(raw), sep=";", encoding="latin-1", engine="python")

    df.columns = [str(column).strip() for column in df.columns]
    required = {"Frage", "Typ", "Antwortmöglichkeiten", "Richtige Antworten"}
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"Fehlende Spalten: {', '.join(sorted(missing))}")

    return _df_to_questions(df)


@st.cache_resource
def get_database() -> Client:
    try:
        url = st.secrets["supabase"]["url"]
        key = st.secrets["supabase"]["service_role_key"]
    except (FileNotFoundError, KeyError) as exc:
        raise RuntimeError(
            "Supabase-Zugangsdaten fehlen. Lege in den Streamlit-Secrets "
            "[supabase] url und service_role_key an."
        ) from exc
    return create_client(url, key)


def get_quiz(db: Client, quiz_id: str) -> Optional[dict]:
    response = db.table("quizzes").select("*").eq("quiz_id", quiz_id).limit(1).execute()
    return response.data[0] if response.data else None


def save_result(
    db: Client,
    name: str,
    answers: Dict[str, str],
    scores: Dict[str, float],
    questions: List[Question],
    quiz_id: str,
) -> None:
    answers_by_number = {
        f"F{i}": answers.get(question.prompt, "")
        for i, question in enumerate(questions, start=1)
    }
    scores_by_number = {
        f"F{i}": round(float(scores.get(question.prompt, 0.0)), 2)
        for i, question in enumerate(questions, start=1)
    }

    db.table("quiz_results").insert(
        {
            "quiz_id": quiz_id,
            "participant_name": name.strip(),
            "submitted_at": utc_now().isoformat(),
            "total": round(float(sum(scores.values())), 2),
            "answers": answers_by_number,
            "scores": scores_by_number,
        }
    ).execute()


def admin_password_is_valid(password: str) -> bool:
    try:
        expected_hash = st.secrets["admin"]["password_sha256"]
    except (FileNotFoundError, KeyError):
        return False
    actual_hash = hashlib.sha256(password.encode("utf-8")).hexdigest()
    return hmac.compare_digest(actual_hash, expected_hash)


def results_to_dataframe(rows: List[dict]) -> pd.DataFrame:
    flattened: List[dict] = []
    for row in rows:
        item = {
            "Name": row.get("participant_name", ""),
            "Zeit": row.get("submitted_at", ""),
            "Total": row.get("total", 0),
        }
        answers = row.get("answers") or {}
        scores = row.get("scores") or {}
        for key in sorted(answers, key=lambda value: int(value[1:])):
            item[f"{key} Antwort"] = answers[key]
            item[f"{key} Punkte"] = scores.get(key, 0)
        flattened.append(item)
    return pd.DataFrame(flattened)


st.set_page_config(page_title="Quiz", page_icon="❓", layout="centered")

try:
    db = get_database()
except RuntimeError as error:
    st.error(str(error))
    st.stop()

try:
    params = dict(st.query_params)
except AttributeError:
    raw_params = st.experimental_get_query_params()
    params = {key: value[0] if isinstance(value, list) else value for key, value in raw_params.items()}


if "quiz_id" in params:
    quiz_id = str(params["quiz_id"]).strip()
    quiz = get_quiz(db, quiz_id)

    if not quiz:
        st.error("Quiz nicht gefunden – ist der Link korrekt?")
        st.stop()

    if utc_now() > parse_timestamp(quiz["expires_at"]):
        st.error("Dieser Quiz-Link ist abgelaufen.")
        st.stop()

    questions = [Question(**question) for question in quiz["questions"]]

    st.title("📋 Online-Quiz")
    name = st.text_input("Dein Name", key="participant_name").strip()

    if name:
        st.divider()
        answers: Dict[str, str] = {}
        for index, question in enumerate(questions, start=1):
            if question.qtype == "mc":
                selected = st.multiselect(
                    f"{index}. {question.prompt}",
                    question.options,
                    key=f"q{index}",
                )
                answers[question.prompt] = "|".join(selected)
            else:
                answers[question.prompt] = st.text_input(
                    f"{index}. {question.prompt}",
                    key=f"q{index}",
                )

        if st.button("Antworten absenden", type="primary", disabled=st.session_state.get("submitted", False)):
            scores = {
                question.prompt: (
                    question.weight * mc_grader(answers[question.prompt], question.correct)
                    if question.qtype == "mc"
                    else question.weight * open_grader(answers[question.prompt], question.correct)
                )
                for question in questions
            }
            try:
                save_result(db, name, answers, scores, questions, quiz_id)
            except Exception as error:
                st.error(f"Das Ergebnis konnte nicht gespeichert werden: {error}")
            else:
                st.session_state["submitted"] = True
                st.success("Danke, deine Antworten wurden gespeichert!")
                st.balloons()

        if st.session_state.get("submitted") and st.button("Nächste Person"):
            for key in list(st.session_state):
                if key.startswith("q") or key in {"participant_name", "submitted"}:
                    del st.session_state[key]
            st.rerun()

else:
    st.title("📋 Quiz-Administration")

    with st.expander("Neues Quiz erstellen", expanded=True):
        uploaded_file = st.file_uploader(
            "Fragen-Datei (CSV / Excel)",
            type=["csv", "xls", "xlsx"],
        )

        if st.button("Quiz-Link erstellen", type="primary"):
            if not uploaded_file:
                st.error("Bitte zuerst eine Datei auswählen.")
                st.stop()

            try:
                questions = load_questions(uploaded_file)
                quiz_id = uuid.uuid4().hex[:12]
                created_at = utc_now()
                expires_at = created_at + timedelta(days=QUIZ_VALID_DAYS)

                db.table("quizzes").insert(
                    {
                        "quiz_id": quiz_id,
                        "created_at": created_at.isoformat(),
                        "expires_at": expires_at.isoformat(),
                        "questions": [asdict(question) for question in questions],
                    }
                ).execute()
            except Exception as error:
                st.error(f"Quiz konnte nicht erstellt werden: {error}")
            else:
                query = f"?quiz_id={quiz_id}"
                st.success("Quiz erfolgreich angelegt.")
                st.link_button("➡️ Zum Quiz", query)
                st.code(query)
                st.info(f"Gültig bis: {expires_at.astimezone().strftime('%d.%m.%Y %H:%M %Z')}")

    st.header("Quiz-Ergebnisse")
    admin_password = st.text_input("Admin-Passwort", type="password")
    quiz_to_check = st.text_input("Quiz-ID")

    if st.button("Ergebnisse laden"):
        if not admin_password_is_valid(admin_password):
            st.error("Admin-Passwort ist falsch oder noch nicht eingerichtet.")
        elif not quiz_to_check.strip():
            st.error("Bitte eine Quiz-ID eingeben.")
        else:
            try:
                response = (
                    db.table("quiz_results")
                    .select("participant_name,submitted_at,total,answers,scores")
                    .eq("quiz_id", quiz_to_check.strip())
                    .order("submitted_at")
                    .execute()
                )
            except Exception as error:
                st.error(f"Ergebnisse konnten nicht geladen werden: {error}")
            else:
                if not response.data:
                    st.warning("Für diese Quiz-ID gibt es noch keine Ergebnisse.")
                else:
                    result_df = results_to_dataframe(response.data)
                    st.dataframe(result_df, use_container_width=True)
                    st.download_button(
                        "CSV herunterladen",
                        result_df.to_csv(index=False).encode("utf-8-sig"),
                        file_name=f"Quiz_{quiz_to_check.strip()}_Ergebnisse.csv",
                        mime="text/csv",
                    )
