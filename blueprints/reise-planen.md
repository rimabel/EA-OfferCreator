# Blueprint: Reise planen (Tagesplan & Sehenswürdigkeiten)
**Engine:** 2 — Blueprint  
**Datei:** `blueprints/reise-planen.md`  
**Workflow:** Reise-Informationsblatt — Schritt 1 von 2

---

## Zweck
Alle Reisedaten vom Nutzer erfassen, Sehenswürdigkeiten per Wikipedia-Equipment holen und bestätigen lassen sowie den Tagesplan berechnen. Die Anzahl der Sights ist frei wählbar (Standard: 5). Ergebnis ist eine bestätigte `tagesplan.json`, die direkt als Eingabe für `blueprints/reise-pdf-erstellen.md` dient.

---

## Pflichtfelder (vor Start prüfen)

| Feld | Pflicht | Beispiel |
|---|---|---|
| Reiseziel | Ja | „Paris" |
| Ankunftszeit am Ziel | Ja | „11:00" |
| Abfahrtszeit vom Ziel | Ja | „20:30" |
| Abfahrtsort (Heimatort) | Ja | „Völklingen" |
| Geplante Ankunft zu Hause | Nein | „02:30" |
| Kunden-E-Mail | Ja | „mustermann@example.de" |
| Kundenname (für Anrede) | Ja | „Herr Mustermann" |

> ⚠️ **Wenn ein Pflichtfeld fehlt: STOP. Beim Nutzer nachfragen — niemals raten oder schätzen.**

---

## Namenskonvention: `normalized-ziel`

Für Ordner- und Dateinamen wird das Reiseziel normiert:

| Regel | Beispiel |
|---|---|
| Kleinbuchstaben | `Paris` → `paris` |
| Leerzeichen → Bindestriche | `Bad Homburg` → `bad-homburg` |
| ä → ae | `Düsseldorf` → `dusseldorf`* |
| ö → oe | `Köln` → `koeln` |
| ü → ue | `München` → `muenchen` |
| ß → ss | `Straße` → `strasse` |

*Vollständiges Beispiel: `Düsseldorf` → `duesseldorf`*

---

## Schritt-für-Schritt-Workflow

### Schritt 1 — Alle Eingaben sammeln

- Alle Felder aus der Pflichtfeldtabelle prüfen.
- Fehlt ein Pflichtfeld → **STOP**, beim Nutzer nachfragen.
- Erst wenn alle Pflichtfelder vorliegen, mit Schritt 2 fortfahren.

---

### Schritt 2 — Sehenswürdigkeiten holen (Wikipedia-Vorschlag)

Den Nutzer zuerst fragen:
> „Wie viele Sehenswürdigkeiten soll der Tagesplan umfassen? (Standard: 5)"

Equipment-Aufruf mit gewählter Anzahl:

```
PYTHONIOENCODING=utf-8 python equipment/reise_info_wikipedia.py --ziel "[ZIEL]" --count [N]
```

- Die zurückgelieferten Sehenswürdigkeiten als nummerierte Liste ausgeben, z. B.:

  ```
  1. Eiffelturm
  2. Louvre
  3. Notre-Dame
  4. Musée d'Orsay
  5. Arc de Triomphe
  ```

- Den Nutzer fragen:
  > „Möchtest du eine oder mehrere Sehenswürdigkeiten ersetzen oder weitere hinzufügen?"

- **Fehlerfall:** Gibt das Skript einen Fehler (Exit-Code ≠ 0) zurück → **STOP**, Fehlermeldung vollständig an den Nutzer weitergeben. Nicht automatisch neu starten.

---

### Schritt 3 — Sehenswürdigkeiten ggf. anpassen

**Ersetzen** (z. B. „Ersetze 3 mit Versailles"):

```
PYTHONIOENCODING=utf-8 python equipment/reise_info_wikipedia.py --ziel "[ZIEL]" --replace [N] "[Neuer Name]"
```

**Hinzufügen** (z. B. „Füge Versailles hinzu"):

```
PYTHONIOENCODING=utf-8 python equipment/reise_info_wikipedia.py --ziel "[ZIEL]" --add "[Name]"
```

- Nach jeder Änderung die aktualisierte Liste anzeigen.
- Änderungen wiederholen, bis der Nutzer die Liste ausdrücklich bestätigt.
- **Fehlerfall:** Gibt das Skript einen Fehler zurück → **STOP**, Fehlermeldung an den Nutzer weitergeben.

> ⚠️ **Niemals zur nächsten Änderung oder zum nächsten Schritt weitergehen, ohne dass der Nutzer die aktuelle Liste bestätigt hat.**

---

### Schritt 4 — Aktivitäten pro Halt generieren

Der Architect generiert für jeden bestätigten Halt 2–3 typische Aktivitäten und einen Ankunfts-Block.

**Vorlage (Architect erstellt diesen Inhalt):**

```
Ankunft in [ZIEL]:
• [z.B. Kurze Pause für die Gäste]
• [z.B. Organisation & Erklärung des Programms]

1. Halt: [Name Sight 1]:
• [Aktivität 1]
• [Aktivität 2]

2. Halt: [Name Sight 2]:
• [Aktivität 1]
• [Aktivität 2]

... (für alle N Sights — je nach bestätigter Anzahl)

Optional (nur wenn ein optionaler Halt gewünscht ist):
• [Optionaler Halt Name, Zeitraum, Aktivitäten]
```

---

Der Architect fragt:
> „Sollen diese Aktivitäten so übernommen werden? (Kann vor der PDF-Erstellung angepasst werden)"

Nach Bestätigung schreibt der Architect die Datei:
`equipment/temp/reise-[normalized-ziel]/aktivitaeten.json`

Format:

```json
{
  "ankunft": ["Kurze Pause für die Gäste", "Organisation & Erklärung des Programms"],
  "sights": [
    ["Aktivität 1a", "Aktivität 1b"],
    ["Aktivität 2a", "Aktivität 2b"],
    "... (ein Array pro Sight — so viele wie bestätigt)"
  ],
  "optional": {
    "name": "Gärten von Versailles",
    "von": "19:45",
    "bis": "20:30",
    "aktivitaeten": ["Nur wenn genügend Zeit vorhanden ist", "Abendlicher Spaziergang"]
  }
}
```

> ⚠️ Das `optional`-Feld wird **nur hinzugefügt**, wenn ein optionaler Halt gewünscht ist.  
> ⚠️ **Ohne ausdrückliche Bestätigung der Aktivitäten nicht zum nächsten Schritt weitergehen.**

---

### Schritt 5 — Tagesplan berechnen

Equipment-Aufruf (vollständig mit allen Parametern):

```
PYTHONIOENCODING=utf-8 python equipment/reise_tagesplan.py \
  --ziel "[ZIEL]" \
  --ankunft "[ANKUNFTSZEIT]" \
  --abfahrt "[ABFAHRTSZEIT]" \
  --heimatort "[HEIMATORT]" \
  --heimankunft "[HEIMANKUNFT]" \
  --json "equipment/temp/reise-[normalized-ziel]/sights.json" \
  --aktivitaeten "equipment/temp/reise-[normalized-ziel]/aktivitaeten.json"
```

> 📝 **Hinweis:** `--heimankunft` nur angeben, wenn der Nutzer eine geplante Ankunftszeit zu Hause genannt hat. Andernfalls den Parameter weglassen.

- **Fehlerfall:** Gibt das Skript einen Fehler zurück → **STOP**, Fehlermeldung vollständig an den Nutzer weitergeben. Nicht automatisch neu starten.

---

### Schritt 6 — Tagesplan präsentieren und bestätigen  <!-- ehemals Schritt 5 -->

- Den berechneten Tagesplan als Tabelle ausgeben, z. B.:

  | Zeit | Programmpunkt |
  |---|---|
  | 11:00 | Ankunft in Paris |
  | 11:30 | Eiffelturm |
  | 13:00 | Louvre |
  | … | … |
  | 20:30 | Abfahrt nach Hause |

- Den Nutzer fragen:
  > „Sieht der Tagesplan so aus? Weiter mit PDF-Erstellung?"

- **Wenn der Nutzer Änderungen wünscht:**
  - Darauf hinweisen, dass manuelle Anpassungen direkt in der JSON-Datei möglich sind:
    ```
    equipment/temp/reise-[normalized-ziel]/tagesplan.json
    ```
  - Erst nachdem der Nutzer bestätigt, dass die Änderungen vorgenommen sind, weitergehen.

> ⚠️ **Ohne ausdrückliche Bestätigung des Tagesplans nicht zum nächsten Blueprint wechseln.**

---

### Schritt 7 — Weiter mit PDF-Erstellung

Sobald der Tagesplan bestätigt ist, mit dem nächsten Blueprint fortfahren:

> **→ `blueprints/reise-pdf-erstellen.md`**

Folgende Daten übergeben (zusammenfassen und dem Nutzer bestätigen):

| Übergabe | Wert |
|---|---|
| Reiseziel | `[ZIEL]` |
| normalized-ziel | `[normalized-ziel]` |
| Kundenname | `[KUNDENNAME]` |
| Kunden-E-Mail | `[EMAIL]` |
| JSON-Pfad (Tagesplan) | `equipment/temp/reise-[normalized-ziel]/tagesplan.json` |
| JSON-Pfad (Aktivitäten) | `equipment/temp/reise-[normalized-ziel]/aktivitaeten.json` |

---

## Qualitätsprüfung

- [ ] Alle Pflichtfelder vorhanden und vollständig?
- [ ] Anzahl Sehenswürdigkeiten mit Nutzer abgestimmt und bestätigt?
- [ ] Aktivitäten pro Halt generiert und vom Nutzer bestätigt?
- [ ] `aktivitaeten.json` korrekt erzeugt (`equipment/temp/reise-[normalized-ziel]/aktivitaeten.json`)?
- [ ] Tagesplan berechnet und vom Nutzer freigegeben?
- [ ] `tagesplan.json` korrekt erzeugt (`equipment/temp/reise-[normalized-ziel]/tagesplan.json`)?
- [ ] Übergabedaten für nächsten Blueprint vollständig?

---

## Technische Hinweise

- **Python-Binary:** `python` (nicht `python3`) — Windows-Umgebung
- **Encoding:** Immer `PYTHONIOENCODING=utf-8` voranstellen
- **Temp-Ordner:** `equipment/temp/reise-[normalized-ziel]/` — wird vom Equipment-Skript angelegt
- **Fehlerbehandlung:** Bei jedem Skript-Fehler (Exit-Code ≠ 0) sofort stoppen und den vollen Fehlertext an den Nutzer weitergeben — kein automatischer Neustart ohne Bestätigung

---

## Fehlerregeln (verbindlich)

| Situation | Regel |
|---|---|
| Pflichtfeld fehlt | STOP — beim Nutzer nachfragen |
| Equipment-Skript gibt Fehler zurück | STOP — Fehler vollständig melden, auf Anweisung warten |
| Nutzer hat Liste / Tagesplan noch nicht bestätigt | STOP — nicht eigenständig weitergehen |
| Nächster Schritt unklar | STOP — beim Nutzer nachfragen |
