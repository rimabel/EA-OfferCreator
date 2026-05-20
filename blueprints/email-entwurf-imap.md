# Blueprint: E-Mail-Entwurf via IMAP erstellen
**Engine:** 2 — Blueprint  
**Datei:** `blueprints/email-entwurf-imap.md`  
**Equipment:** `equipment/email_entwurf_imap.py`  
**Abhängigkeit:** Blueprint `angebot-erstellen.md` muss zuerst abgeschlossen sein.

---

## Zweck
Fertiges Angebot als PDF in einen E-Mail-Entwurf umwandeln und automatisch im Drafts-Ordner des IMAP-Servers speichern.

---

## Voraussetzungen (vor Start prüfen)

- [ ] Angebot als `.docx` fertig erstellt (Blueprint `angebot-erstellen.md`)
- [ ] PDF des Angebots vorhanden
- [ ] E-Mail-Text fertig (aus Vorlage in `angebot-erstellen.md` Schritt 8)
- [ ] `.env` Datei (Variable `IMAP_PASSWORD`) gesetzt
- [ ] Empfänger-E-Mail-Adresse bekannt

---

## Schritt-für-Schritt-Workflow

### Schritt 1 — DOCX zu PDF konvertieren
```python
from docx2pdf import convert

# PDF-Name: NUR Angebotsnummer — kein _Garamond_4_ Suffix!
convert("[ANGEBOTSNUMMER]_Garamond_4_.docx", "[ANGEBOTSNUMMER].pdf")
# Output: [ANGEBOTSNUMMER].pdf
```

### Schritt 2 — E-Mail-Text als .txt speichern
```bash
# E-Mail-Text aus dem Angebots-Workflow in eine Datei schreiben
cat > /home/claude/email_text.txt << 'EOF'
[E-MAIL-TEXT HIER EINFÜGEN]
EOF
```

### Schritt 3 — Umgebungsvariable prüfen
```bash
# Passwort muss gesetzt sein – NIEMALS im Code speichern!
echo $IMAP_PASSWORD  # sollte einen Wert zurückgeben
```
> ⚠️ Falls nicht gesetzt: `IMAP_PASSWORD=IhrPasswort` in `.env` Datei eintragen ausführen.

### Schritt 4 — Entwurf via IMAP speichern
```bash
# PYTHONIOENCODING=utf-8 ist auf Windows zwingend erforderlich
PYTHONIOENCODING=utf-8 python equipment/email_entwurf_imap.py \
  --an "[EMPFAENGER-EMAIL]" \
  --betreff "Ihr Reiseangebot [ANGEBOTSNUMMER] – [ABFAHRTSORT] ↔ [ZIELORT]" \
  --text email_text.txt \
  --pdf [ANGEBOTSNUMMER].pdf \
  --angebotsnr "[ANGEBOTSNUMMER]"
```

### Schritt 5 — Ergebnis prüfen
- Skript meldet: `✅ Entwurf erfolgreich gespeichert in 'Drafts'`
- E-Mail-Client öffnen → Entwürfe → Entwurf prüfen
- PDF-Anhang vorhanden?
- Text korrekt?

### Schritt 6 — Archivieren
```bash
mkdir -p archiv/[ANGEBOTSNUMMER]
mv [ANGEBOTSNUMMER]_Garamond_4_.docx archiv/[ANGEBOTSNUMMER]/
mv [ANGEBOTSNUMMER].pdf              archiv/[ANGEBOTSNUMMER]/
```

---

## IMAP-Konfiguration

| Parameter | Wert |
|---|---|
| Server | `mail.belahmer-reisen.de` |
| Port | `143` |
| Verbindung | `STARTTLS` |
| Benutzer | `info@belahmer-reisen.de` |
| Passwort | `.env` Datei (Variable `IMAP_PASSWORD`) |
| Drafts-Ordner | `Drafts` (ggf. anpassen) |

> ⚠️ Falls der Drafts-Ordner nicht gefunden wird: Das Skript listet beim Start alle verfügbaren Ordner auf. Den korrekten Namen in `email_entwurf_imap.py` Zeile `DRAFTS_FOLDER` anpassen.

---

## Fehlerbehebung

| Fehler | Lösung |
|---|---|
| `IMAP_PASSWORD nicht gesetzt` | `in `.env` eintragen: `IMAP_PASSWORD=IhrPasswort` im Terminal |
| `Ordner nicht gefunden` | Skript-Output prüfen, `DRAFTS_FOLDER` anpassen |
| `IMAP-Fehler: LOGIN failed` | Passwort prüfen, ggf. App-Passwort verwenden |
| `PDF nicht gefunden` | Pfad prüfen, Schritt 1 wiederholen |

---

## Sicherheitshinweise

- Das Passwort **niemals** in den Code schreiben
- **Niemals** in CLAUDE.md oder Blueprints speichern
- Nur als Umgebungsvariable (`IMAP_PASSWORD`) verwenden
- `.env` Datei niemals in Git einchecken (siehe `.gitignore`)
