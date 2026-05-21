# Blueprint: Reise-Informationsblatt PDF erstellen & versenden
**Engine:** 2 — Blueprint  
**Datei:** `blueprints/reise-pdf-erstellen.md`  
**Equipment (Windows):** `equipment/reise_pdf_erstellen.py`, `equipment/email_entwurf_imap.py`  
**Equipment (Linux/Remote):** `equipment/reise_pdf_erstellen_linux.py`, `equipment/email_entwurf_imap.py`  
**Abhängigkeit:** Blueprint `reise-planen.md` muss vollständig abgeschlossen sein (Schritt 2 von 2).

---

## Zweck
Aus den in Blueprint `reise-planen.md` bestätigten Daten ein Reise-Informationsblatt als PDF erstellen, als E-Mail-Entwurf im Drafts-Ordner speichern und anschließend archivieren.

---

## Vorbedingungen (vor Start prüfen)

Folgende Daten und Dateien müssen aus Blueprint `reise-planen.md` vorliegen:

| Feld | Beispiel |
|---|---|
| Reiseziel | Paris |
| Kundenname (mit Anrede) | Herr Mustermann |
| Kunden-E-Mail | mustermann@example.de |
| Abfahrtsort / Heimatort | Völklingen |
| Reisetag (Datum der Reise) | 22.05.2026 |
| Bestätigte `sights.json` | `equipment/temp/reise-[normalized-ziel]/sights.json` |
| Bestätigter `tagesplan.json` | `equipment/temp/reise-[normalized-ziel]/tagesplan.json` |

> ⚠️ **Wenn eine Vorbedingung fehlt: STOP. Blueprint `reise-planen.md` zuerst abschließen.**

**Hinweis zum `[normalized-ziel]`:** Kleinbuchstaben, Umlaute ersetzen, Leerzeichen durch Bindestriche.  
Beispiele: `paris`, `strassburg`, `bad-homburg`

**Hinweis zum `[ZIELORT]`:** Proper Case, Umlaute ersetzen.  
Beispiele: `Paris`, `Strassburg`, `Bad-Homburg`

---

## Schritt-für-Schritt-Workflow

### Schritt 1 — Wasserzeichen-Entscheidung

Den Nutzer fragen:

> **Soll das PDF ein Wasserzeichen „BELAHMER REISEN" auf der Tagesplan-Seite erhalten?**  
> (Ja → `--watermark` wird hinzugefügt / Nein → kein Wasserzeichen)

---

### Schritt 2 — PDF erstellen

Je nach Antwort:

**Mit Wasserzeichen:**
```bash
PYTHONIOENCODING=utf-8 python equipment/reise_pdf_erstellen.py \
  --ziel "[ZIEL]" \
  --datum "[REISETAG]" \
  --watermark \
  --sights "equipment/temp/reise-[normalized-ziel]/sights.json" \
  --tagesplan "equipment/temp/reise-[normalized-ziel]/tagesplan.json"
```

**Ohne Wasserzeichen:**
```bash
PYTHONIOENCODING=utf-8 python equipment/reise_pdf_erstellen.py \
  --ziel "[ZIEL]" \
  --datum "[REISETAG]" \
  --sights "equipment/temp/reise-[normalized-ziel]/sights.json" \
  --tagesplan "equipment/temp/reise-[normalized-ziel]/tagesplan.json"
```

> **Auf Linux / Remote-Agenten** statt `reise_pdf_erstellen.py` das Linux-Skript verwenden  
> (Voraussetzung: `sudo apt install libreoffice`):
> ```bash
> python equipment/reise_pdf_erstellen_linux.py \
>   --ziel "[ZIEL]" \
>   --datum "[REISETAG]" \
>   --sights "equipment/temp/reise-[normalized-ziel]/sights.json" \
>   --tagesplan "equipment/temp/reise-[normalized-ziel]/tagesplan.json"
> ```

**Erwartete Ausgabedateien:**

| Datei | Beispiel |
|---|---|
| `BR-REISE-[ZIELORT]_Garamond_4_.docx` | `BR-REISE-Paris_Garamond_4_.docx` |
| `BR-REISE-[ZIELORT].pdf` | `BR-REISE-Paris.pdf` |

> ⚠️ **Fehlerbehandlung:** Falls das Skript mit einem Fehler abbricht (Exit-Code ≠ 0): STOP. Fehler dem Nutzer melden. Nicht weiter fortfahren, bis das Problem behoben ist.

---

### Schritt 3 — PDF visuell prüfen

Den Nutzer auffordern, das PDF zu öffnen und folgende Punkte zu prüfen:

- [ ] Header korrekt (Firmenlogo, Adresse, Titel)?
- [ ] Tagesplan vollständig und mit richtigen Uhrzeiten?
- [ ] Sehenswürdigkeiten mit Fotos korrekt dargestellt?
- [ ] Zielort und Kundenname stimmen?

> ❓ **Warten auf Bestätigung des Nutzers, bevor mit Schritt 3 fortgefahren wird.**

---

### Schritt 4 — E-Mail-Text erstellen

Datei `email_reise_text.txt` mit folgendem Inhalt erstellen (Platzhalter ersetzen):

```
Sehr geehrter [KUNDENNAME],

im Anhang finden Sie das Reiseprogramm für Ihren geplanten Ausflug nach [ZIEL].

Das Dokument enthält:
→ Den Tagesplan mit Uhrzeiten und Programmpunkten
→ Eine Übersicht der schönsten Sehenswürdigkeiten mit Fotos

Wir wünschen Ihnen und Ihrer Gruppe eine schöne und unvergessliche Reise!

Bei Fragen stehen wir Ihnen gerne zur Verfügung.

Mit freundlichen Grüßen,
Nabil Belahmer
Belahmer Reisen
Kurpfalzstr 3 | 67734 Katzweiler
Tel.: +49 6301 6689790 | info@belahmer-reisen.de
```

**Platzhalter:**

| Platzhalter | Wert |
|---|---|
| `[KUNDENNAME]` | Vollständige Anrede + Name (z. B. `Herr Mustermann`) |
| `[ZIEL]` | Reiseziel (z. B. `Paris`) |

---

### Schritt 5 — IMAP-Passwort prüfen

```bash
# Passwort muss in .env gesetzt sein – NIEMALS direkt im Code speichern!
# Prüfen ob IMAP_PASSWORD in .env vorhanden ist
```

> ⚠️ Falls `IMAP_PASSWORD` in der `.env`-Datei fehlt: STOP. Den Nutzer bitten, den Eintrag `IMAP_PASSWORD=IhrPasswort` in die `.env`-Datei einzutragen, bevor dieser Schritt ausgeführt wird.

---

### Schritt 6 — E-Mail-Entwurf via IMAP speichern

```bash
PYTHONIOENCODING=utf-8 python equipment/email_entwurf_imap.py \
  --an "[KUNDEN-EMAIL]" \
  --betreff "Ihr Reiseprogramm [ZIEL] – [REISETAG] | Belahmer Reisen" \
  --text email_reise_text.txt \
  --pdf "BR-REISE-[ZIELORT].pdf" \
  --angebotsnr "BR-REISE-[ZIELORT]-[DATUM]-[NACHNAME]"
```

**Erwartete Ausgabe des Skripts:**
```
✅ Entwurf erfolgreich gespeichert in 'Drafts'
```

> ⚠️ **Fehlerbehandlung:** Falls das Skript mit einem Fehler abbricht (Exit-Code ≠ 0): STOP. Fehler dem Nutzer melden. Nicht weiter fortfahren.

---

### Schritt 7 — Archivieren

> 🔒 **Bestätigung erforderlich (permissions.md):** Vor dem Verschieben von Dateien den Nutzer informieren und auf Bestätigung warten.

**Archiv-Ordner erstellen:**

Format: `archiv/BR-REISE-[ZIELORT]-[DATUM]-[NACHNAME]/`

| Platzhalter | Wert |
|---|---|
| `[ZIELORT]` | Proper Case, Umlaute ersetzt (z. B. `Paris`, `Strassburg`) |
| `[DATUM]` | Heutiges Datum im Format `YYYY-MM-DD` (z. B. `2026-05-20`) |
| `[NACHNAME]` | Nur der Nachname (z. B. `Mustermann` aus `Herr Mustermann`) |

**Beispiel:** `archiv/BR-REISE-Paris-2026-05-22-Mustermann/`

```bash
mkdir -p archiv/BR-REISE-[ZIELORT]-[DATUM]-[NACHNAME]
mv BR-REISE-[ZIELORT]_Garamond_4_.docx archiv/BR-REISE-[ZIELORT]-[DATUM]-[NACHNAME]/
mv BR-REISE-[ZIELORT].pdf              archiv/BR-REISE-[ZIELORT]-[DATUM]-[NACHNAME]/
mv email_reise_text.txt                archiv/BR-REISE-[ZIELORT]-[DATUM]-[NACHNAME]/
```

---

### Schritt 8 — Temp-Ordner aufräumen (optional)

> 🔒 **Bestätigung erforderlich (permissions.md):** Den Nutzer fragen, ob der Temp-Ordner gelöscht werden soll.

```bash
# Nur nach ausdrücklicher Bestätigung durch den Nutzer ausführen!
rm -rf equipment/temp/reise-[normalized-ziel]/
```

---

### Schritt 9 — Abschluss

Den Nutzer informieren:

> **Fertig!** Der E-Mail-Entwurf mit dem Reiseprogramm für **[ZIEL]** liegt im Drafts-Ordner bereit.  
> Bitte im E-Mail-Client prüfen und ggf. vor dem Versenden anpassen.

---

## Fehlerbehebung

| Fehler | Lösung |
|---|---|
| `reise_pdf_erstellen.py` bricht ab | Fehlermeldung prüfen, ggf. `sights.json` / `tagesplan.json` prüfen |
| Word öffnet DOCX als schreibgeschützt (Protected View) | DOCX nach `%TEMP%` kopieren vor COM-Konvertierung — bereits im Equipment eingebaut (Zone.Identifier-Entfernung + TEMP-Ordner) |
| `SaveAs`-Fehler bei COM-Konvertierung | `ExportAsFixedFormat` statt `SaveAs` verwenden — bereits im Equipment so implementiert |
| Word hält DOCX-Datei gesperrt | `Stop-Process -Name WINWORD -Force` ausführen, dann erneut versuchen |
| `IMAP_PASSWORD nicht gesetzt` | In `.env` eintragen: `IMAP_PASSWORD=IhrPasswort` |
| `Drafts-Ordner nicht gefunden` | Skript-Output prüfen; `DRAFTS_FOLDER` in `email_entwurf_imap.py` anpassen |
| `IMAP-Fehler: LOGIN failed` | Passwort prüfen, ggf. App-Passwort verwenden |
| `PDF nicht gefunden` | Pfad prüfen; Schritt 1 erneut ausführen |
| `sights.json fehlt` | Blueprint `reise-planen.md` neu starten — Daten unvollständig |
| PDF-Viewer sperrt PDF beim Archivieren | PDF-Viewer schließen oder `Stop-Process` auf den Viewer-Prozess; dann `mv` erneut ausführen |

---

## Sicherheitshinweise

- Das IMAP-Passwort **niemals** in Code oder Blueprints schreiben
- Nur als Umgebungsvariable (`IMAP_PASSWORD`) in der `.env`-Datei verwenden
- `.env`-Datei niemals in Git einchecken (siehe `.gitignore`)
