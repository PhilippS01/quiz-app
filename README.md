# Quiz-App – dauerhafte Speicherung für mindestens 7 Tage

Diese Version speichert Quizze und Ergebnisse dauerhaft in **Supabase/PostgreSQL**. Dadurch gehen die Daten bei einem Neustart oder Redeployment der Streamlit-App nicht mehr verloren.

## Projektstruktur

```text
Quiz/
├── .streamlit/
│   └── secrets.toml.example
├── quizzes/
│   └── quiz_testfragen.csv
├── results/
│   └── .gitkeep
├── app.py
├── README.md
├── requirements.txt
└── supabase_setup.sql
```

> Der Ordner `results/` bleibt nur erhalten, damit die Projektstruktur deiner bisherigen App entspricht. Die neuen Ergebnisse werden nicht dort, sondern sicher in Supabase gespeichert.

## Was wurde geändert?

- Quizze und Ergebnisse werden in Supabase statt im lokalen Dateisystem gespeichert.
- Quizlinks sind genau **7 Tage** gültig.
- Zeitstempel werden in UTC verarbeitet, um Zeitzonenfehler zu vermeiden.
- Die Ergebnisansicht ist mit einem Admin-Passwort geschützt.
- Multiple-Choice-Antworten werden beim Upload validiert.
- Mehrfaches Absenden derselben Sitzung wird verhindert.
- Ergebnisse können weiterhin als CSV heruntergeladen werden.
- Die Beispiel-CSV enthält bei Multiple Choice die richtigen Antworttexte statt Optionsnummern.

## TODO – Einrichtung

### 1. Supabase-Projekt erstellen

- [ ] Auf Supabase ein neues Projekt erstellen.
- [ ] Im Projekt den **SQL Editor** öffnen.
- [ ] Den vollständigen Inhalt von `supabase_setup.sql` ausführen.
- [ ] Prüfen, ob die Tabellen `quizzes` und `quiz_results` angelegt wurden.

### 2. Zugangsdaten besorgen

- [ ] In Supabase die **Project URL** kopieren.
- [ ] Den geheimen **service_role key** kopieren.
- [ ] Den Key niemals in GitHub, `app.py` oder eine öffentliche Datei schreiben.

### 3. Admin-Passwort vorbereiten

Erzeuge aus deinem gewünschten Passwort einen SHA-256-Hash:

```bash
python -c "import hashlib; print(hashlib.sha256('MEIN_SICHERES_PASSWORT'.encode()).hexdigest())"
```

- [ ] `MEIN_SICHERES_PASSWORT` durch dein echtes Passwort ersetzen.
- [ ] Den ausgegebenen Hash kopieren.

### 4. Streamlit-Secrets eintragen

Bei Streamlit Community Cloud:

1. App öffnen.
2. **Settings** auswählen.
3. **Secrets** öffnen.
4. Folgenden Inhalt eintragen und die Platzhalter ersetzen:

```toml
[supabase]
url = "https://DEIN-PROJEKT.supabase.co"
service_role_key = "DEIN-SERVICE-ROLE-KEY"

[admin]
password_sha256 = "DEIN-SHA256-PASSWORTHASH"
```

- [ ] Project URL eingesetzt.
- [ ] `service_role_key` eingesetzt.
- [ ] Passwort-Hash eingesetzt.
- [ ] Secrets gespeichert.

Für einen lokalen Test kannst du `.streamlit/secrets.toml.example` kopieren und in `.streamlit/secrets.toml` umbenennen. Diese echte Datei darf nicht veröffentlicht werden.

### 5. Dateien in GitHub ersetzen

- [ ] Die bisherige `app.py` durch diese `app.py` ersetzen.
- [ ] Die bisherige `requirements.txt` durch diese `requirements.txt` ersetzen.
- [ ] `supabase_setup.sql` und `README.md` mit hochladen.
- [ ] Optional die korrigierte Datei `quizzes/quiz_testfragen.csv` übernehmen.
- [ ] Änderungen committen und pushen.

Streamlit sollte danach automatisch neu deployen. Falls nicht, im Streamlit-Dashboard einen Reboot oder Redeploy auslösen.

## Lokaler Start

Python 3.10 oder neuer wird empfohlen.

```bash
pip install -r requirements.txt
```

Danach eine echte `.streamlit/secrets.toml` anlegen und starten:

```bash
streamlit run app.py
```

## Funktionstest nach dem Deployment

- [ ] Administrationsseite ohne `quiz_id` öffnen.
- [ ] `quizzes/quiz_testfragen.csv` hochladen.
- [ ] Einen Quizlink erzeugen.
- [ ] Den Link in einem privaten Browserfenster öffnen.
- [ ] Quiz mit einem Testnamen absenden.
- [ ] Auf der Administrationsseite Admin-Passwort und Quiz-ID eingeben.
- [ ] Prüfen, ob das Ergebnis angezeigt und als CSV geladen werden kann.
- [ ] Die Streamlit-App neu starten oder redeployen.
- [ ] Danach erneut prüfen, ob Quiz und Ergebnis noch vorhanden sind.

## CSV-Format

Erwartete Spalten:

```text
Frage;Typ;Antwortmöglichkeiten;Richtige Antworten;Gewicht
```

Für Multiple Choice (`mc`) müssen unter `Richtige Antworten` die **Antworttexte** stehen:

```csv
Welche Zahl ist größer als 3?;mc;"2; 4; 5";"4;5";1.5
```

Nicht verwenden:

```csv
Welche Zahl ist größer als 3?;mc;"2; 4; 5";"1;3";1.5
```

Bei offenen Fragen (`open`) bleibt `Antwortmöglichkeiten` leer:

```csv
Wie heißt die Hauptstadt von Frankreich?;open;;Paris;1.0
```

## Aufbewahrungsdauer

Die Links laufen nach sieben Tagen ab. Die Daten werden dabei nicht automatisch gelöscht, sondern bleiben in Supabase erhalten. Soll später auch eine automatische Löschung nach sieben Tagen erfolgen, muss dafür zusätzlich ein geplanter Datenbank-Job eingerichtet werden.

Die Dauer des Links kannst du in `app.py` ändern:

```python
QUIZ_VALID_DAYS = 7
```

## Sicherheit

- Den `service_role_key` ausschließlich in Streamlit-Secrets speichern.
- Keine echte `.streamlit/secrets.toml` in GitHub hochladen.
- Ein langes, einzigartiges Admin-Passwort verwenden.
- Das Supabase-Projekt nicht öffentlich freigeben.


--------------------------
###### GPT antwort #######
--------------------------

Hier ist die fertig strukturierte ZIP-Datei:

Quiz_Supabase_Fix.zip herunterladen⁠￼

Die Struktur darin sieht so aus:

Quiz/
├── .streamlit/
│   └── secrets.toml.example
├── quizzes/
│   └── quiz_testfragen.csv
├── results/
│   └── .gitkeep
├── app.py
├── README.md
├── requirements.txt
├── supabase_setup.sql
└── .gitignore

Die README.md enthält bereits:

* eine Erklärung aller Änderungen,
* eine vollständige TODO-Checkliste,
* die Supabase-Einrichtung,
* die Streamlit-Secrets,
* den Passwort-Hash-Befehl,
* die GitHub- und Deployment-Schritte,
* einen vollständigen Funktionstest,
* das korrekte CSV-Format,
* Sicherheitshinweise.

Was du danach machen musst

1. ZIP entpacken

Entpacke die Datei zunächst auf deinem Computer.

Dein bisheriges Projekt solltest du vorher als Sicherung kopieren.

2. Supabase-Projekt erstellen

Erstelle bei Supabase ein neues Projekt.

Öffne anschließend:

Supabase → SQL Editor

Kopiere dort den gesamten Inhalt dieser Datei hinein:

supabase_setup.sql

Führe das SQL-Skript aus. Es erstellt die Tabellen:

quizzes
quiz_results

3. Supabase-Zugangsdaten kopieren

Du benötigst aus deinem Supabase-Projekt:

Project URL
service_role key

Der service_role key ist geheim. Er darf nicht direkt in app.py oder in GitHub stehen.

4. Passwort-Hash erstellen

Öffne ein Terminal und führe Folgendes aus:

python -c "import hashlib; print(hashlib.sha256('MEIN_SICHERES_PASSWORT'.encode()).hexdigest())"

Ersetze dabei:

MEIN_SICHERES_PASSWORT

durch dein gewünschtes Admin-Passwort.

Kopiere danach den ausgegebenen langen Hash.

5. Streamlit-Secrets eintragen

Öffne deine App bei Streamlit Community Cloud und gehe zu:

App → Settings → Secrets

Trage dort Folgendes ein:

[supabase]
url = "https://DEIN-PROJEKT.supabase.co"
service_role_key = "DEIN-SERVICE-ROLE-KEY"
[admin]
password_sha256 = "DEIN-SHA256-PASSWORTHASH"

Ersetze alle drei Platzhalter.

6. Dateien in GitHub ersetzen

Ersetze in deinem bisherigen Repository mindestens:

app.py
requirements.txt

Lade zusätzlich hoch:

README.md
supabase_setup.sql
.gitignore
.streamlit/secrets.toml.example

Den echten service_role key darfst du nicht in secrets.toml.example eintragen.

7. Deployment abwarten

Nach dem Commit sollte Streamlit die App automatisch neu deployen.

Falls nicht:

Streamlit Dashboard → App → Reboot

Danach testen

1. Öffne die App ohne Quiz-ID.
2. Lade quizzes/quiz_testfragen.csv hoch.
3. Erstelle einen Quizlink.
4. Öffne den Link in einem privaten Browserfenster.
5. Fülle das Quiz aus.
6. Kopiere die Quiz-ID.
7. Öffne wieder die Administrationsseite.
8. Trage Admin-Passwort und Quiz-ID ein.
9. Lade die Ergebnisse.
10. Starte die Streamlit-App neu.
11. Prüfe erneut, ob das Ergebnis noch vorhanden ist.

Bleibt das Ergebnis nach dem Neustart erhalten, funktioniert die dauerhafte Speicherung korrekt.

Der Ordner results/ ist in der ZIP nur enthalten, damit die Struktur deiner bisherigen App entspricht. Die Ergebnisse werden jetzt nicht mehr dort gespeichert, sondern in Supabase.