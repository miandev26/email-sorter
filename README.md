# email-sorter

Sortiert Jakobs E-Mails nach Wichtigkeit/Absender.

## Features

- **Gmail (IMAP)**: Inbox scannen, Regeln auswerten, dann optional in Labels verschieben (Gmail IMAP-Ordner) oder als gelesen markieren.
- **Proton Mail (Browser/Playwright)**: Best-effort UI-Automation (Login + Inbox lesen + in Ordner verschieben). Proton hat keine öffentliche IMAP-Unterstützung ohne Bridge; daher UI.
- **Regel-Engine**: Priorität anhand von Absendern, Domain, Subject-Keywords, "List-Unsubscribe" usw.

## Quickstart

### 1) Konfiguration

Kopiere `config.example.json` nach `config.json` und passe Regeln an.

### 2) Gmail Credentials

Setze Umgebungsvariablen (empfohlen via `.env`):

- `GMAIL_ADDRESS` (z.B. `aij168429@gmail.com`)
- `GMAIL_APP_PASSWORD` (App-Passwort; bei 2FA nötig)

> Hinweis: Im Workspace liegt **kein** Gmail-Passwort. Nutze ein App-Passwort.

### 3) Proton Credentials

- `PROTON_ADDRESS` = `jaclaw95@proton.me`
- `PROTON_PASSWORD` = `...`

> In `TOOLS.md` steht ein Passwort-Beispiel; **prüfe** das vor Nutzung.

### 4) Ausführen

```bash
python3 -m emailsorter.cli gmail --config config.json --dry-run
python3 -m emailsorter.cli gmail --config config.json --apply

python3 -m emailsorter.cli proton --config config.json --headed --dry-run
python3 -m emailsorter.cli proton --config config.json --headed --apply
```

## Sicherheit

- `--dry-run` zeigt nur, was passieren **würde**.
- `--apply` führt Änderungen im Mailkonto aus (Flags/Move).

## Status Proton

Die Proton-UI kann sich ändern. Das Playwright-Script ist bewusst defensiv und loggt Selektoren/Schritte. Eventuell müssen Selektoren angepasst werden.
