# Blueprint: Mietbus-Angebot erstellen
**Engine:** 2 — Blueprint  
**Datei:** `blueprints/angebot-erstellen.md`  
**Vorlage:** `BR-A2026-0003_Garamond_4_.docx`

---

## Zweck
Einen neuen Mietbus-Angebot auf Basis der Vorlage erstellen und alle kundenspezifischen Daten anpassen.

---

## Pflichtfelder (vor Start prüfen)

| Feld | Beispiel |
|---|---|
| Kundenname & Anrede | Frau Alina Onofrei |
| Abfahrtsort | Wiesbaden |
| Zielort (exakte Adresse) | Flughafenring 2, 44319 Dortmund |
| Datum Hinfahrt | 06.06.2026 |
| Uhrzeit Hinfahrt (Abfahrt) | 03:54 Uhr |
| Datum Rückfahrt | 20.06.2026 |
| Uhrzeit Rückfahrt (Abfahrt) | 07:54 Uhr |
| Gruppengröße (PAX) | 33 |
| Preis pro Fahrt (brutto) | 1.250,00 € |

> ⚠️ **Wenn ein Feld fehlt: STOP. Beim Nutzer nachfragen.**

---

## Schritt-für-Schritt-Workflow

### Schritt 1 — Angebotsnummer vergeben
- Letzte Nummer aus Vorlage ablesen und um 1 erhöhen
- Format: `BR-A[JAHR]-[VIERSTELLIG]`
- Beispiel: BR-A2026-0003 → **BR-A2026-0004**

### Schritt 2 — Strecke berechnen
- **Immer beim Nutzer erfragen** — keine Websuche, kein Schätzen
- Fahrtzeit berechnen: `km / 80` (Reisebus-Faustregel), auf 10 Minuten aufrunden

### Schritt 3 — Zeiten berechnen
- Standby = Abfahrtszeit − 30 Minuten
- Beispiel: Abfahrt 03:54 → Standby 03:24

### Schritt 4 — Preise & Fristen berechnen
- Netto = Brutto / 1,19 (auf 2 Dezimalstellen runden)
- MwSt. = Brutto − Netto
- Rechnungsbetrag = Summe aller Bruttopreise (Hin + Rück)
- **Angebotsfrist** = `min(Erstellungsdatum + 7 Tage, Datum Hinfahrt)` — nie nach dem Abfahrtsdatum

### Schritt 5 — Dokument bearbeiten (Windows)
```python
import shutil, zipfile, os

# 1. Saubere Vorlage nach unpacked/ kopieren
shutil.copy('template/word/document.xml', 'unpacked/word/document.xml')

# 2. XML in unpacked/word/document.xml direkt bearbeiten (Edit-Tool)
#    Alle Platzhalter laut Änderungsliste unten ersetzen

# 3. Packen
output = '[NEUE-NUMMER]_Garamond_4_.docx'
with zipfile.ZipFile(output, 'w', zipfile.ZIP_DEFLATED) as zf:
    for root, dirs, files in os.walk('unpacked'):
        for file in files:
            fp = os.path.join(root, file)
            zf.write(fp, os.path.relpath(fp, 'unpacked').replace(os.sep, '/'))
```

### Schritt 6 — XML-Änderungsliste

| Feld | Wo im XML |
|---|---|
| Erstellungsdatum | `Katzweiler, den [DATUM]` |
| Angebots-Nr. | `<w:t>BR-A2026-XXXX</w:t>` (Infotabelle) |
| Angebotsfrist | Datum in Infotabelle + Hinweis 1 |
| Fahrt (Infotabelle) | Route + Datumsbereich |
| Titel (rot) | `Angebot für Fahrt: ...` |
| Streckenlänge | `Einfache Fahrtstrecke: X km (ca. X Std.)` |
| Hinfahrt-Zeile (Leistungstabelle) | Auftragsnr., Standby, Abfahrt, Start, Ziel, Datum, PAX, Preis |
| Rückfahrt-Zeile (Leistungstabelle) | Auftragsnr., Standby, Abfahrt, Start, Ziel, Datum, PAX, Preis |
| Zwischensumme Netto | Summentabelle |
| MwSt. 19 % | Summentabelle |
| Rechnungsbetrag | Summentabelle |
| Hinweis 3 | Angebotsnummer aktualisieren |
| Ablaufplan Hinfahrt | Datum, Route, Standby, Abfahrt, Details, PAX |
| Ablaufplan Rückfahrt | Datum, Route, Standby, Abfahrt, Details, PAX |

### Schritt 7 — Qualitätsprüfung
- [ ] Alle Daten korrekt?
- [ ] Preise stimmen (Netto + MwSt. = Brutto)?
- [ ] Angebotsnummer überall konsistent?
- [ ] Ablaufplan auf neuer Seite?
- [ ] Validierung durch pack.py bestanden?

### Schritt 8 — E-Mail-Text erstellen (auf Wunsch)

Vorlage ausfüllen:

```
Betreff: Ihr Reiseangebot [ANGEBOTSNUMMER] – [ABFAHRTSORT] ↔ [ZIELORT]

Sehr geehrte/r [ANREDE] [NACHNAME],

vielen Dank für Ihre Anfrage. Wir freuen uns, Ihnen unser individuelles Angebot
für Ihre geplante Gruppenreise zu unterbreiten.

Im Anhang finden Sie unser Angebot [ANGEBOTSNUMMER] als PDF mit allen Details
zu Ihrer Fahrt von [ABFAHRTSORT] nach [ZIELORT] und zurück für [PAX] Reisende.

Zur Übersicht:
• Hinfahrt: [DATUM HINFAHRT], Abfahrt [ABFAHRTSZEIT HINFAHRT] Uhr ab [ABFAHRTSORT]
• Rückfahrt: [DATUM RÜCKFAHRT], Abfahrt [ABFAHRTSZEIT RÜCKFAHRT] Uhr ab [ZIELORT]
• Gesamtbetrag: [GESAMTBETRAG] € (inkl. 19 % MwSt.)

Das Angebot ist gültig bis zum [ANGEBOTSFRIST]. Sollten Sie Fragen haben oder
Änderungswünsche bestehen, stehen wir Ihnen jederzeit gerne zur Verfügung.

Zur Auftragsbestätigung bitten wir Sie, uns Ihre Buchung schriftlich per E-Mail
unter Angabe der Angebotsnummer [ANGEBOTSNUMMER] zu bestätigen.

Wir würden uns freuen, Sie und Ihre Gruppe begleiten zu dürfen.

Mit freundlichen Grüßen

Nabil Belahmer
Belahmer Reisen
Kurpfalzstr 3 | 67734 Katzweiler
Tel.: +49 6301 6689790
info@belahmer-reisen.de
```

---

## Technische Hinweise

- Schriftart: **Garamond** (bereits in Vorlage gesetzt)
- Ablaufplan: `<w:pageBreakBefore w:val="1"/>` im `<w:pPr>` des Ablaufplan-Absatzes
- XML-Fehler: Nach jeder Preisänderung prüfen ob `<w:r>` korrekt geschlossen ist
- Stornofristen: Bereits in Vorlage enthalten — nur ändern wenn ausdrücklich gewünscht

---

## Standard-Stornofristen

1. Bis 30 Tage vor Fahrtantritt: kostenlose Stornierung
2. 15–29 Tage vor Fahrtantritt: 25 % des Rechnungsbetrags
3. 7–14 Tage vor Fahrtantritt: 50 % des Rechnungsbetrags
4. 2–6 Tage vor Fahrtantritt: 75 % des Rechnungsbetrags
5. Weniger als 48 Stunden / Nichterscheinen: 100 % des Rechnungsbetrags
