# Google Drive OAuth (Desktop/Manual) – Setup & Root Listing

## Hintergrund
Für Zugriff auf Google Drive via API brauchst du ein **OAuth 2.0 Client** (Client ID + Client Secret) und einen OAuth-Flow, der ein **Refresh Token** erzeugt.

> Wichtig: Ein **Client Secret alleine** reicht nicht. Du brauchst die komplette `client_secrets.json` (enthält Client ID, Secret, Redirect URIs).

## Voraussetzungen
1. In Google Cloud Console:
   - Projekt auswählen/erstellen
   - **Google Drive API** aktivieren
   - **OAuth consent screen** konfigurieren
   - OAuth Client anlegen: **Desktop app**
   - JSON herunterladen

2. Lege die Datei als `client_secrets.json` im Repo-Root ab (nicht committen!).

## Installation
Python deps (ohne venv):

```bash
pip install --user google-api-python-client google-auth-httplib2 google-auth-oauthlib
```

## OAuth Flow (Manual/Console)
Run:

```bash
python3 tools/drive_oauth_list_root.py --scopes drive.metadata.readonly
```

Beim ersten Run:
- Script druckt eine URL
- URL im Browser öffnen
- Zugriff bestätigen
- den angezeigten Code zurück ins Terminal kopieren

Dann schreibt das Script `token.json` (enthält Refresh Token).

## Dateien im Root auflisten
Nach erfolgreichem OAuth listet das Script automatisch die Root-Dateien. Format:

```
<name>\t<mimeType>\t<id>\t<size>
```

## Sicherheit
- `token.json` ist sensitv (Refresh Token). **Nicht committen**, sicher speichern.
- Falls Token geleakt: in Google Account → Security → Third-party access widerrufen.
