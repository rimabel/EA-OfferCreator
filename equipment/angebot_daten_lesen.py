"""
Liest eine befüllte Angebots-DOCX und gibt die extrahierten Feldwerte als JSON aus.

Verwendung:
  python equipment/angebot_daten_lesen.py --docx archiv/BR-A2026-0008/BR-A2026-0008_Garamond_4_.docx

Ausgabe: JSON auf stdout
Exit-Code: 0 = Erfolg, 1 = Fehler
"""
import argparse
import json
import re
import sys
import zipfile
import xml.etree.ElementTree as ET

NS = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"


def extract_text_from_xml(xml_content: bytes) -> list[str]:
    """Gibt alle Textläufe aus document.xml als zusammengesetzte Absätze zurück."""
    root = ET.fromstring(xml_content)
    paragraphs = []
    for p in root.iter(f"{{{NS}}}p"):
        runs = []
        for t in p.iter(f"{{{NS}}}t"):
            if t.text:
                runs.append(t.text)
        text = "".join(runs).strip()
        if text:
            paragraphs.append(text)
    return paragraphs


def extract_table_rows(xml_content: bytes) -> list[tuple[str, str]]:
    """Gibt (label, value)-Paare aus Tabellenzellen zurück."""
    root = ET.fromstring(xml_content)
    rows = []
    for tbl in root.iter(f"{{{NS}}}tbl"):
        for tr in tbl.iter(f"{{{NS}}}tr"):
            cells = []
            for tc in tr.findall(f"{{{NS}}}tc"):
                cell_text = []
                for t in tc.iter(f"{{{NS}}}t"):
                    if t.text:
                        cell_text.append(t.text)
                cells.append("".join(cell_text).strip())
            if len(cells) >= 2:
                rows.append((cells[0], cells[1]))
    return rows


def match_label(label: str, pattern: str) -> bool:
    return pattern.lower() in label.lower()


def find_by_label(rows: list[tuple[str, str]], *patterns: str) -> str | None:
    for label, value in rows:
        if all(match_label(label, p) for p in patterns):
            return value or None
    return None


def extract_fields(paragraphs: list[str], table_rows: list[tuple[str, str]]) -> dict:
    fields: dict = {}

    # --- Aus Tabellen-Zeilen ---
    fields["angebotsnummer"] = find_by_label(table_rows, "angebots-nr") or find_by_label(table_rows, "best.-nr")
    fields["erstellungsdatum"] = find_by_label(table_rows, "erstellungsdatum") or find_by_label(table_rows, "datum", "erstell")
    fields["angebotsfrist"] = find_by_label(table_rows, "angebotsfrist") or find_by_label(table_rows, "frist")
    fields["fahrt"] = find_by_label(table_rows, "fahrt")

    # Abfahrtsort + Zielort aus "Fahrt"-Zeile (Format: "OrtA – OrtB | Datumsbereich")
    fahrt_val = fields.get("fahrt") or ""
    fahrt_match = re.match(r"^(.+?)\s*[–-]\s*(.+?)\s*\|", fahrt_val)
    if fahrt_match:
        fields["abfahrtsort"] = fahrt_match.group(1).strip()
        fields["zielort"] = fahrt_match.group(2).strip()
    else:
        fields["abfahrtsort"] = None
        fields["zielort"] = None

    # Preise aus Preis-Spalten-Werten
    preis_h = None
    preis_r = None
    for label, value in table_rows:
        if "hinfahrt" in label.lower() and re.search(r"\d", value):
            preis_h = value.replace("€", "").strip()
        elif "rückfahrt" in label.lower() and re.search(r"\d", value):
            preis_r = value.replace("€", "").strip()

    # Preise aus Preisspalte (letzte Spalte in Leistungstabelle)
    for label, value in table_rows:
        if re.search(r"\d+[.,]\d{2}\s*€", value):
            clean = value.replace("€", "").strip()
            if "hinfahrt" in label.lower() and not preis_h:
                preis_h = clean
            elif "rückfahrt" in label.lower() and not preis_r:
                preis_r = clean

    fields["preis_h"] = preis_h
    fields["preis_r"] = preis_r

    fields["netto_gesamt"] = find_by_label(table_rows, "netto")
    if fields["netto_gesamt"]:
        fields["netto_gesamt"] = fields["netto_gesamt"].replace("€", "").strip()

    fields["mwst_gesamt"] = find_by_label(table_rows, "mwst") or find_by_label(table_rows, "19 %")
    if fields["mwst_gesamt"]:
        fields["mwst_gesamt"] = fields["mwst_gesamt"].replace("€", "").strip()

    fields["brutto_gesamt"] = find_by_label(table_rows, "rechnungsbetrag") or find_by_label(table_rows, "brutto")
    if fields["brutto_gesamt"]:
        fields["brutto_gesamt"] = fields["brutto_gesamt"].replace("€", "").strip()

    # --- Aus Absätzen (Ablaufplan-Zeilen) ---
    for p in paragraphs:
        # "Standby: 07:30 Uhr" oder "[STANDBY_H]"
        m = re.search(r"Standby:\s*(\d{1,2}[:h]\d{2})", p)
        if m and "standby_h" not in fields:
            fields["standby_h"] = m.group(1)
        # "Abfahrt: 08:00 Uhr"
        m = re.search(r"Abfahrt:\s*(\d{1,2}[:h]\d{2})", p)
        if m and "abfahrt_h" not in fields:
            fields["abfahrt_h"] = m.group(1)
        # PAX aus Auftragsbeschreibung
        m = re.search(r"\b(\d{1,3})\s*(?:Personen|Fahrgäste|PAX)\b", p, re.IGNORECASE)
        if m and "pax" not in fields:
            fields["pax"] = m.group(1)

    # PAX aus Tabellenzelle (mittlere Spalte in Leistungstabelle)
    if not fields.get("pax"):
        for label, value in table_rows:
            if re.match(r"^\d{1,3}$", value.strip()):
                if any(kw in label.lower() for kw in ["abfahrt", "hinfahrt", "start", "fahrt", "route"]):
                    fields["pax"] = value.strip()
                    break

    # Auftragsnummern aus Absätzen (#DDMM001-Format)
    auftragsnr_list = re.findall(r"#\d{6,}", " ".join(paragraphs))
    fields["auftragsnr_h"] = auftragsnr_list[0] if len(auftragsnr_list) > 0 else None
    fields["auftragsnr_r"] = auftragsnr_list[1] if len(auftragsnr_list) > 1 else None

    # Datum Hin-/Rückfahrt aus Ablaufplan
    datum_list = re.findall(r"\b\d{2}\.\d{2}\.\d{4}\b", " ".join(paragraphs))
    unique_dates = list(dict.fromkeys(datum_list))
    fields["datum_hinfahrt"] = unique_dates[0] if len(unique_dates) > 0 else None
    fields["datum_rueckfahrt"] = unique_dates[1] if len(unique_dates) > 1 else None

    # Anrede / Nachname aus Briefanrede
    for p in paragraphs:
        m = re.match(r"Sehr geehrte/r\s+(\S+)\s+(\S+)", p)
        if m:
            fields["anrede"] = m.group(1)
            fields["nachname"] = m.group(2).rstrip(",")
            break

    # KM / Fahrtzeit aus Leistungsbeschreibung
    for p in paragraphs:
        m = re.search(r"(\d+)\s*km", p)
        if m:
            fields["km"] = m.group(1)
        m = re.search(r"ca\.\s*([\d,]+\s*(?:Std|h|Stunden))", p, re.IGNORECASE)
        if m:
            fields["fahrtzeit"] = m.group(1)

    # ABFAHRTSORT_VOLL / ZIELORT_VOLL aus Ablaufplan-Zeile (letzte Spalte Details)
    for label, value in table_rows:
        if "start:" in value.lower() and not fields.get("abfahrtsort_voll"):
            m = re.search(r"Start:\s*(.+?)(?:\n|$|Ziel:|Fahrtart:)", value, re.IGNORECASE)
            if m:
                fields["abfahrtsort_voll"] = m.group(1).strip()
        if "ziel:" in value.lower() and not fields.get("zielort_voll"):
            m = re.search(r"Ziel:\s*(.+?)(?:\n|$|Start:|Fahrtart:)", value, re.IGNORECASE)
            if m:
                fields["zielort_voll"] = m.group(1).strip()

    # Zeitangaben aus Ablaufplan-Tabelle
    for label, value in table_rows:
        if re.match(r"^\d{1,2}:\d{2}$", value.strip()):
            col = label.lower()
            if "standby" in col and "standby_h" not in fields:
                fields["standby_h"] = value.strip()
            elif "abfahrt" in col and "abfahrt_h" not in fields:
                fields["abfahrt_h"] = value.strip()

    return fields


def main() -> None:
    parser = argparse.ArgumentParser(description="Angebots-DOCX auslesen")
    parser.add_argument("--docx", required=True, help="Pfad zur Angebots-DOCX")
    args = parser.parse_args()

    try:
        with zipfile.ZipFile(args.docx, "r") as z:
            xml_content = z.read("word/document.xml")
    except FileNotFoundError:
        print(f"Fehler: Datei nicht gefunden: {args.docx}", file=sys.stderr)
        sys.exit(1)
    except KeyError:
        print("Fehler: word/document.xml nicht in der DOCX gefunden", file=sys.stderr)
        sys.exit(1)

    paragraphs = extract_text_from_xml(xml_content)
    table_rows = extract_table_rows(xml_content)
    fields = extract_fields(paragraphs, table_rows)

    print(json.dumps(fields, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
