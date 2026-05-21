# Blueprint: Auftragsbestätigung erstellen
**Engine:** 2 — Blueprint  
**Datei:** `blueprints/auftragsbestaetigung-erstellen.md`  
**Vorlage:** `template-auftragsbestaetigung/`

---

## Zweck
Aus einem bestehenden Angebot (BR-A…) eine verbindliche Auftragsbestätigung (BR-AB…) erstellen, optional mit Anpassungen an Abfahrtszeiten, Orten oder Preis. Wird als E-Mail-Entwurf mit PDF-Anhang gespeichert und im Archiv-Ordner des Angebots abgelegt.

---

## Schritt 1 — Angebotsnummer entgegennehmen

- Nutzer gibt die Angebotsnummer an (Format: `BR-A2026-XXXX`)
- Architect prüft: Existiert `archiv/[NUMMER]/[NUMMER]_Garamond_4_.docx`?
- Wenn nicht gefunden: **STOP. Beim Nutzer nachfragen.**

---

## Schritt 2 — Angebotsdaten auslesen

Equipment aufrufen:
```bash
python equipment/angebot_daten_lesen.py --docx archiv/[NUMMER]/[NUMMER]_Garamond_4_.docx
```

Architect zeigt die extrahierten Werte als Tabelle:

| Feld | Extrahierter Wert |
|---|---|
| Angebotsnummer | … |
| Abfahrtsort | … |
| Zielort | … |
| Datum Hinfahrt | … |
| Datum Rückfahrt | … |
| Standby Hinfahrt | … |
| Abfahrt Hinfahrt | … |
| Standby Rückfahrt | … |
| Abfahrt Rückfahrt | … |
| PAX | … |
| Preis Hinfahrt | … |
| Preis Rückfahrt | … |
| Netto gesamt | … |
| MwSt. gesamt | … |
| Rechnungsbetrag | … |
| Auftragsnr. Hinfahrt | … |
| Auftragsnr. Rückfahrt | … |
| KM / Fahrtzeit | … |

Fehlende Felder (`null`): **Beim Nutzer erfragen — nie raten.**

---

## Schritt 3 — Bestätigungs-Nummer vergeben

- Architect scannt `archiv/` nach Ordnern mit Präfix `BR-AB`
- Letzte Nummer + 1 → neue `BR-AB[JAHR]-[VIERSTELLIG]`-Nummer
- Wenn keine BR-AB-Ordner vorhanden: erste Nummer = `BR-AB[JAHR]-0001`
- Nutzer bestätigt die Nummer

---

## Schritt 4 — Anpassungen abfragen

Architect fragt explizit:

> „Sollen für die Bestätigung Felder geändert werden?  
> Mögliche Anpassungen: Abfahrtszeiten, Standby-Zeiten, Abfahrtsort, Zielort, Preis."

Alle Anpassungen notieren. Wenn Preis geändert wird → Netto/MwSt./Brutto neu berechnen:
- Netto = Brutto ÷ 1,19 (2 Dezimalstellen)
- MwSt. = Brutto − Netto

Empfänger-E-Mail-Adresse erfragen (Pflichtfeld für Schritt 7).

---

## Schritt 5 — Vorlage befüllen & packen

```python
import shutil, zipfile, os

# Saubere Bestätigungsvorlage nach unpacked/ kopieren
shutil.copy('template-auftragsbestaetigung/word/document.xml', 'unpacked/word/document.xml')

# Alle Platzhalter im Edit-Tool ersetzen (siehe Änderungsliste unten)

# Packen
output = '[BESTAETIGUNG_NR]_Garamond_4_.docx'
with zipfile.ZipFile(output, 'w', zipfile.ZIP_DEFLATED) as zf:
    for root, dirs, files in os.walk('unpacked'):
        for file in files:
            fp = os.path.join(root, file)
            zf.write(fp, os.path.relpath(fp, 'unpacked').replace(os.sep, '/'))
```

### Platzhalter-Mapping

| Platzhalter in Vorlage | Wert |
|---|---|
| `[BESTAETIGUNG_NR]` | Neue BR-AB-Nummer (Schritt 3) |
| `[BESTAETIGUNG_DATUM]` | Heutiges Datum (TT.MM.JJJJ) |
| `[ANGEBOTS_REF]` | Original-Angebotsnummer (BR-A…) |
| `[ABFAHRTSORT]` | Aus Schritt 2 (ggf. angepasst) |
| `[ZIELORT]` | Aus Schritt 2 (ggf. angepasst) |
| `[ABFAHRTSORT_VOLL]` | Vollständige Abfahrtsadresse |
| `[ZIELORT_VOLL]` | Vollständige Zieladresse |
| `[DATUM_HINFAHRT]` | Aus Schritt 2 |
| `[DATUM_RÜCKFAHRT]` | Aus Schritt 2 (falls Rückfahrt) |
| `[DATUMSBEREICH]` | z.B. „22.–25.05.2026" |
| `[AUFTRAGSNR_H]` | Aus Schritt 2 |
| `[AUFTRAGSNR_R]` | Aus Schritt 2 (falls Rückfahrt) |
| `[STANDBY_H]` | Aus Schritt 2 (ggf. angepasst) |
| `[ABFAHRT_H]` | Aus Schritt 2 (ggf. angepasst) |
| `[STANDBY_R]` | Aus Schritt 2 (ggf. angepasst) |
| `[ABFAHRT_R]` | Aus Schritt 2 (ggf. angepasst) |
| `[PAX]` | Aus Schritt 2 |
| `[KM]` | Aus Schritt 2 |
| `[FAHRTZEIT]` | Aus Schritt 2 |
| `[ANREDE]` | Aus Schritt 2 |
| `[NACHNAME]` | Aus Schritt 2 |
| `[PREIS_H]` | Aus Schritt 2 (ggf. angepasst) |
| `[PREIS_R]` | Aus Schritt 2 (ggf. angepasst) |
| `[NETTO_GESAMT]` | Berechnet oder aus Schritt 2 |
| `[MWST_GESAMT]` | Berechnet oder aus Schritt 2 |
| `[BRUTTO_GESAMT]` | Aus Schritt 2 (ggf. angepasst) |

> ⚠️ **Alle Platzhalter müssen ersetzt sein — kein `[…]` darf im fertigen Dokument übrig bleiben.**

---

## Schritt 6 — PDF konvertieren

```bash
python -c "from docx2pdf import convert; convert('[BESTAETIGUNG_NR]_Garamond_4_.docx', '[BESTAETIGUNG_NR].pdf')"
```

Qualitätsprüfung:
- [ ] Titel lautet „Auftragsbestätigung für Fahrt: …"
- [ ] Best.-Nr. zeigt die BR-AB-Nummer
- [ ] Bezug: Angebot zeigt die BR-A-Nummer
- [ ] Alle Daten, Zeiten und Preise korrekt
- [ ] Kein Platzhalter `[…]` mehr sichtbar
- [ ] Stornofristen vorhanden

---

## Schritt 7 — E-Mail-Entwurf erstellen

E-Mail-Text als `email_bestaetigung_text.txt` speichern:

```
Sehr geehrte/r [ANREDE] [NACHNAME],

vielen Dank für Ihr Vertrauen in Belahmer Reisen.

Wir bestätigen hiermit verbindlich Ihre Buchung gemäß beigefügter
Auftragsbestätigung Nr. [BESTAETIGUNG_NR]
(Bezug: Angebot [ANGEBOTS_REF]).

Bitte prüfen Sie die Bestätigung sorgfältig und teilen Sie uns
eventuelle Änderungswünsche umgehend mit.

Für Rückfragen stehen wir Ihnen gerne zur Verfügung.

Mit freundlichen Grüßen,
Nabil Belahmer
Belahmer Reisen
Kurpfalzstr 3 | 67734 Katzweiler
Tel.: +49 6301 6689790 | info@belahmer-reisen.de
```

Equipment aufrufen:
```bash
PYTHONIOENCODING=utf-8 python equipment/email_entwurf_imap.py \
  --an [EMPFAENGER_EMAIL] \
  --betreff "Auftragsbestätigung [BESTAETIGUNG_NR] – [ZIELORT], [DATUM_HINFAHRT]" \
  --text email_bestaetigung_text.txt \
  --pdf [BESTAETIGUNG_NR].pdf \
  --angebotsnr [BESTAETIGUNG_NR]
```

Bestätigung: Entwurf im E-Mail-Client prüfen.

---

## Schritt 8 — Archivieren

Alle Dateien in den **bestehenden Angebots-Archiv-Ordner** verschieben:

```
archiv/[ORIGINAL_ANGEBOTSNR]/[BESTAETIGUNG_NR]_Garamond_4_.docx
archiv/[ORIGINAL_ANGEBOTSNR]/[BESTAETIGUNG_NR].pdf
archiv/[ORIGINAL_ANGEBOTSNR]/email_bestaetigung_text.txt
```

Beispiel:
```
archiv/BR-A2026-0008/BR-AB2026-0001_Garamond_4_.docx
archiv/BR-A2026-0008/BR-AB2026-0001.pdf
archiv/BR-A2026-0008/email_bestaetigung_text.txt
```

> Angebot und Bestätigung liegen gemeinsam im selben Archiv-Ordner.

---

## Technische Hinweise

- Vorlage: `template-auftragsbestaetigung/` (nicht `template/`)
- Schriftart: Garamond (bereits in Vorlage gesetzt)
- PDF-Konvertierung: `docx2pdf` (Windows)
- Kein eigener Archiv-Ordner für Bestätigungen — immer in den Angebots-Ordner
- Stornofristen: bereits in Vorlage enthalten — nur ändern wenn ausdrücklich gewünscht
