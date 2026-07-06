# Betternotes 📚

Jeden Schulmorgen um ca. **6:00 Uhr** eine E-Mail mit deiner persönlichen
**Tagesvorbereitung**:

- Nur die Fächer, die du **heute laut Untis** hast (Zwischenüberschrift je Fach)
- **Prägnante Zusammenfassung** der Notizen seit der letzten Stunde
  (aus deinem Goodnotes-Backup, auch Handschrift)
- **Fachbegriffe werden direkt in Klammern dahinter erklärt**
- Abschnitt **„Wichtig für die nächste Stunde"**: offene Aufgaben, Anschlussthemen,
  Schlüsselfragen zur Selbstkontrolle
- An **Sowi-Tagen**: die **5 wichtigsten Nachrichten der letzten 7 Tage**
  (tagesschau), ebenfalls mit erklärten Fachbegriffen
- Als HTML-Mail **und** PDF-Anhang (lässt sich direkt in Goodnotes importieren)

## Wie es funktioniert

```
GitHub Actions (Mo–Fr, kurz vor 6:00 deutscher Zeit)
  1. guard      Zeitfenster + „heute schon gesendet?" prüfen
  2. timetable  WebUntis: Welche Fächer hast du heute? (Ausfälle werden gefiltert)
  3. ingest     Google Drive: neue Goodnotes-Backup-PDFs seit dem letzten Digest,
                Zuordnung zu Fächern über Muster in config.yaml
  4. extract    PDF-Seiten → Claude Vision (liest auch Handschrift)
  5. summarize  Claude: Rückblick + Vorbereitung, Fachbegriffe in Klammern
  6. news       nur an Sowi-Tagen: tagesschau/RSS → Top 5 der Woche
  7. render     HTML + PDF
  8. deliver    E-Mail-Versand
  9. persist    state/state.json wird zurück ins Repo committet
```

Goodnotes hat keine Lese-API – deshalb läuft alles über das eingebaute
**automatische Backup** von Goodnotes nach Google Drive (PDF-Format).

## Einmalige Einrichtung

### 1. Goodnotes (iPad)

1. Goodnotes → Einstellungen → **Cloud & Backup** → **Automatisches Backup** einschalten.
2. Ziel: **Google Drive**, Dateiformat: **PDF**.
3. Notizbücher pro Fach benennen oder in Fach-Ordner legen (z.B. `Mathe`, `Sowi`) –
   die Muster stehen in `config.yaml` unter `subjects[].goodnotes`.

### 2. Google Drive API (Service Account)

1. [console.cloud.google.com](https://console.cloud.google.com) → neues Projekt →
   **Google Drive API aktivieren**.
2. **Service Account** anlegen → JSON-Schlüssel herunterladen.
3. In Google Drive den Backup-Ordner (`GoodNotes`) mit der E-Mail-Adresse des
   Service Accounts **teilen** (Betrachter genügt).
4. Den kompletten JSON-Inhalt als Secret `GDRIVE_SERVICE_ACCOUNT_JSON` hinterlegen.

### 3. WebUntis

Schulname und Server findest du in der Untis-App bzw. in der Login-URL
(z.B. `https://mese.webuntis.com/WebUntis/?school=...` → Server `mese.webuntis.com`).
Secrets: `WEBUNTIS_SERVER`, `WEBUNTIS_SCHOOL`, `WEBUNTIS_USER`, `WEBUNTIS_PASSWORD`.

### 4. Anthropic (Claude)

API-Key unter [console.anthropic.com](https://console.anthropic.com) erstellen →
Secret `ANTHROPIC_API_KEY`. Kosten: grob 5–15 ct pro Schultag (abhängig von der
Seitenzahl deiner Notizen).

### 5. E-Mail-Versand (GMX)

1. GMX → Einstellungen → POP3/IMAP **für externe Programme aktivieren**.
2. Secrets: `SMTP_HOST` = `smtp.gmx.net`, `SMTP_USER` = deine GMX-Adresse,
   `SMTP_PASSWORD` = dein GMX-Passwort (bzw. anwendungsspezifisches Passwort).
3. Empfängerin steht in `config.yaml` (`recipient`).

### 6. Secrets in GitHub eintragen

Repository → **Settings → Secrets and variables → Actions** → alle oben genannten
Secrets anlegen.

### 7. `config.yaml` anpassen

- **`subjects`**: je Fach die Untis-Kürzel (exakt wie im Stundenplan), die
  Goodnotes-Namensmuster und den Anzeigenamen eintragen. `news: true` beim
  Sowi-Eintrag aktiviert den Nachrichten-Block.
- **`fallback_week`**: dein normaler Wochenplan (Anzeigenamen) – wird nur genutzt,
  wenn WebUntis nicht erreichbar ist.

## Testen

```bash
# Tests
pip install -e ".[dev]" && pytest

# Probelauf ohne Mailversand (schreibt HTML/PDF nach out/):
python -m betternotes run --dry-run --output out --date 2026-07-06
```

In GitHub: **Actions → Daily Digest → Run workflow** – mit `dry_run` für einen
Probelauf (Ergebnis als Artefakt) oder mit `force` für einen echten Testversand.

## Betrieb & Verhalten

- Läuft Mo–Fr; am Wochenende/in den Ferien (leerer Stundenplan) kommt keine Mail.
- WebUntis nicht erreichbar → Fallback-Wochenplan, mit Hinweis in der Mail.
- Keine neuen Notizen in einem Fach → trotzdem ein Vorbereitungs-Abschnitt auf
  Basis des bisherigen Stoffs.
- Neue Dateien ohne Fach-Zuordnung erscheinen unter „Sonstiges" in der Mail.
- Bei Fehlern bekommst du eine kurze Fehler-Mail statt eines stillen Ausfalls.
- `state/state.json` merkt sich verarbeitete Dateien und den letzten Versand und
  wird vom Workflow automatisch zurückcommittet.
