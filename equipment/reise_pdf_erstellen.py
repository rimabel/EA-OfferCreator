#!/usr/bin/env python3
"""
Equipment: reise_pdf_erstellen.py
Zweck:  Kombiniertes Reise-PDF aus sights.json + tagesplan.json erstellen.
        Seite 1: Firmen-Header + Tagesplan-Tabelle
        Seite 2+: Sehenswürdigkeiten mit Fotos
        Ausgabe: BR-REISE-[ZIELORT]_Garamond_4_.docx + BR-REISE-[ZIELORT].pdf
Aufruf:
  python equipment/reise_pdf_erstellen.py \\
      --ziel "Paris" \\
      --sights "equipment/temp/reise-paris/sights.json" \\
      --tagesplan "equipment/temp/reise-paris/tagesplan.json"
"""

import argparse
import json
import os
import sys
import unicodedata

from docx import Document
from docx.shared import Cm, Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml.ns import qn
from docx.oxml import OxmlElement

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

COLOR_DARK_RED = RGBColor(0x98, 0x00, 0x00)   # #980000 — header background
COLOR_BURGUNDY = RGBColor(0x6E, 0x14, 0x14)   # #6e1414 — titles / table header bg
COLOR_WHITE    = RGBColor(0xFF, 0xFF, 0xFF)
COLOR_GRAY_ROW = "F2F2F2"                       # alternating row shading (hex, no #)

COMPANY_LINES = [
    "BELAHMER REISEN",
    "Inh. Nabil Belahmer",
    "Kurpfalzstr 3",
    "67734 Katzweiler",
    "E-Mail: info@belahmer-reisen.de",
    "Tel.: +49 6301 6689790",
]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def normalize_ziel(ziel: str) -> str:
    """Convert destination name to filesystem-friendly string.

    Applies NFKD decomposition, strips combining diacritics, maps German
    umlauts, lowercases and replaces spaces with hyphens.
    """
    decomposed = unicodedata.normalize("NFKD", ziel)
    no_accents = "".join(ch for ch in decomposed if unicodedata.category(ch) != "Mn")
    umlaut_table = str.maketrans({
        "ä": "ae", "ö": "oe", "ü": "ue", "ß": "ss",
        "Ä": "ae", "Ö": "oe", "Ü": "ue",
    })
    normalized = no_accents.translate(umlaut_table)
    return normalized.lower().replace(" ", "-")


def set_cell_bg(cell, hex_color: str) -> None:
    """Apply a solid background fill to a table cell (OOXML shading)."""
    tc = cell._tc
    tcPr = tc.get_or_add_tcPr()
    shd = OxmlElement("w:shd")
    shd.set(qn("w:val"), "clear")
    shd.set(qn("w:color"), "auto")
    shd.set(qn("w:fill"), hex_color)
    # Remove any existing shd element first
    existing = tcPr.find(qn("w:shd"))
    if existing is not None:
        tcPr.remove(existing)
    tcPr.append(shd)


def set_cell_no_border(cell) -> None:
    """Remove all borders from a table cell."""
    tc = cell._tc
    tcPr = tc.get_or_add_tcPr()
    tcBorders = OxmlElement("w:tcBorders")
    for side in ("top", "left", "bottom", "right", "insideH", "insideV"):
        border = OxmlElement(f"w:{side}")
        border.set(qn("w:val"), "none")
        border.set(qn("w:sz"), "0")
        border.set(qn("w:space"), "0")
        border.set(qn("w:color"), "auto")
        tcBorders.append(border)
    existing = tcPr.find(qn("w:tcBorders"))
    if existing is not None:
        tcPr.remove(existing)
    tcPr.append(tcBorders)


def set_table_no_border(table) -> None:
    """Remove all borders from the table itself."""
    tbl = table._tbl
    tblPr = tbl.find(qn("w:tblPr"))
    if tblPr is None:
        tblPr = OxmlElement("w:tblPr")
        tbl.insert(0, tblPr)
    tblBorders = OxmlElement("w:tblBorders")
    for side in ("top", "left", "bottom", "right", "insideH", "insideV"):
        border = OxmlElement(f"w:{side}")
        border.set(qn("w:val"), "none")
        border.set(qn("w:sz"), "0")
        border.set(qn("w:space"), "0")
        border.set(qn("w:color"), "auto")
        tblBorders.append(border)
    existing = tblPr.find(qn("w:tblBorders"))
    if existing is not None:
        tblPr.remove(existing)
    tblPr.append(tblBorders)


def add_subtle_inner_border(cell) -> None:
    """Add only the bottom border of a cell (subtle horizontal line)."""
    tc = cell._tc
    tcPr = tc.get_or_add_tcPr()
    tcBorders = OxmlElement("w:tcBorders")

    # Only bottom border — light gray, thin
    bottom = OxmlElement("w:bottom")
    bottom.set(qn("w:val"), "single")
    bottom.set(qn("w:sz"), "4")       # half-point units → 0.5 pt
    bottom.set(qn("w:space"), "0")
    bottom.set(qn("w:color"), "CCCCCC")
    tcBorders.append(bottom)

    existing = tcPr.find(qn("w:tcBorders"))
    if existing is not None:
        tcPr.remove(existing)
    tcPr.append(tcBorders)


def set_paragraph_space(paragraph, before_pt: int = 0, after_pt: int = 0) -> None:
    """Set space before/after a paragraph (in points)."""
    pPr = paragraph._p.get_or_add_pPr()
    spacing = pPr.find(qn("w:spacing"))
    if spacing is None:
        spacing = OxmlElement("w:spacing")
        pPr.append(spacing)
    if before_pt:
        spacing.set(qn("w:before"), str(before_pt * 20))   # twips
    if after_pt:
        spacing.set(qn("w:after"), str(after_pt * 20))


# ---------------------------------------------------------------------------
# Document builder
# ---------------------------------------------------------------------------

def build_document(ziel: str, sights: list, tagesplan: dict, logo_path: str) -> Document:
    doc = Document()

    # --- Page setup: A4, narrow margins ---
    section = doc.sections[0]
    section.page_width  = Cm(21)
    section.page_height = Cm(29.7)
    section.top_margin    = Cm(1)
    section.bottom_margin = Cm(1)
    section.left_margin   = Cm(2)
    section.right_margin  = Cm(2)

    # -----------------------------------------------------------------------
    # PAGE 1: Header + Tagesplan
    # -----------------------------------------------------------------------

    # --- Company header table (2 cols, no border) ---
    header_table = doc.add_table(rows=1, cols=2)
    set_table_no_border(header_table)
    header_table.autofit = False

    # Set column widths: logo col = 3cm, info col = fill rest
    header_table.columns[0].width = Cm(3)
    header_table.columns[1].width = Cm(14)

    logo_cell = header_table.cell(0, 0)
    info_cell = header_table.cell(0, 1)

    # Remove borders on both cells
    set_cell_no_border(logo_cell)
    set_cell_no_border(info_cell)

    # Logo
    logo_para = logo_cell.paragraphs[0]
    logo_para.alignment = WD_ALIGN_PARAGRAPH.LEFT
    logo_run = logo_para.add_run()
    logo_run.add_picture(logo_path, width=Cm(2.5))

    # Company info — dark red background, white bold text
    set_cell_bg(info_cell, "980000")
    info_para = info_cell.paragraphs[0]
    info_para.alignment = WD_ALIGN_PARAGRAPH.LEFT

    for i, line in enumerate(COMPANY_LINES):
        run = info_para.add_run(line)
        run.bold = True
        run.font.color.rgb = COLOR_WHITE
        run.font.size = Pt(10)
        if i < len(COMPANY_LINES) - 1:
            run.add_break()

    # Set cell vertical padding to give the text some breathing room
    for cell in (logo_cell, info_cell):
        tc = cell._tc
        tcPr = tc.get_or_add_tcPr()
        tcMar = OxmlElement("w:tcMar")
        for side in ("top", "left", "bottom", "right"):
            m = OxmlElement(f"w:{side}")
            m.set(qn("w:w"), "80")    # ≈ 0.14 cm
            m.set(qn("w:type"), "dxa")
            tcMar.append(m)
        existing = tcPr.find(qn("w:tcMar"))
        if existing is not None:
            tcPr.remove(existing)
        tcPr.append(tcMar)

    # --- Title paragraph ---
    title_para = doc.add_paragraph()
    set_paragraph_space(title_para, before_pt=12, after_pt=6)
    title_run = title_para.add_run(f"Tagesreise: {ziel}")
    title_run.bold = True
    title_run.font.size = Pt(18)
    title_run.font.color.rgb = COLOR_BURGUNDY

    # --- Tagesplan table (2 cols) ---
    time_rows = tagesplan.get("time_rows", [])
    tplan_table = doc.add_table(rows=1 + len(time_rows), cols=2)
    set_table_no_border(tplan_table)
    tplan_table.autofit = False
    tplan_table.columns[0].width = Cm(4)
    tplan_table.columns[1].width = Cm(13)

    # Header row
    hdr_row = tplan_table.rows[0]
    for cell, text in zip(hdr_row.cells, ["Uhrzeit", "Programmpunkt"]):
        set_cell_bg(cell, "6e1414")
        set_cell_no_border(cell)
        para = cell.paragraphs[0]
        run = para.add_run(text)
        run.bold = True
        run.font.color.rgb = COLOR_WHITE
        run.font.size = Pt(10)

    # Data rows
    for idx, row_data in enumerate(time_rows):
        row = tplan_table.rows[idx + 1]
        row_color = "FFFFFF" if idx % 2 == 0 else COLOR_GRAY_ROW

        for cell, text in zip(row.cells, [row_data.get("zeit", ""), row_data.get("programm", "")]):
            set_cell_bg(cell, row_color)
            add_subtle_inner_border(cell)
            para = cell.paragraphs[0]
            run = para.add_run(text)
            run.font.size = Pt(10)

    # -----------------------------------------------------------------------
    # PAGE BREAK
    # -----------------------------------------------------------------------
    doc.add_page_break()

    # -----------------------------------------------------------------------
    # PAGE 2+: Sehenswürdigkeiten
    # -----------------------------------------------------------------------

    section_title = doc.add_paragraph()
    set_paragraph_space(section_title, before_pt=0, after_pt=6)
    st_run = section_title.add_run("Sehenswürdigkeiten")
    st_run.bold = True
    st_run.font.size = Pt(14)
    st_run.font.color.rgb = COLOR_BURGUNDY

    for sight in sights:
        name = sight.get("name", "")
        image_path = sight.get("image")

        # Sight name heading
        name_para = doc.add_paragraph()
        set_paragraph_space(name_para, before_pt=8, after_pt=4)
        name_run = name_para.add_run(name)
        name_run.bold = True
        name_run.font.size = Pt(12)
        name_run.font.color.rgb = COLOR_BURGUNDY

        # Image or placeholder
        image_ok = (
            image_path is not None
            and isinstance(image_path, str)
            and os.path.isfile(image_path)
        )

        if image_ok:
            img_para = doc.add_paragraph()
            img_run = img_para.add_run()
            # Use Pillow to normalise the image into a BytesIO buffer so that
            # python-docx 1.2.0 can handle JPEGs with ICC-profile APP2 markers
            # (0xFFD8FFE2) which it does not recognise when reading from disk.
            try:
                from PIL import Image as PILImage
                import io as _io
                with PILImage.open(image_path) as pil_img:
                    buf = _io.BytesIO()
                    pil_img.convert("RGB").save(buf, format="JPEG", quality=90)
                    buf.seek(0)
                img_run.add_picture(buf, width=Cm(14))
            except Exception:
                # Pillow unavailable or conversion failed — try direct path
                img_run.add_picture(image_path, width=Cm(14))
            set_paragraph_space(img_para, after_pt=8)
        else:
            placeholder = doc.add_paragraph("[Kein Bild verfügbar]")
            set_paragraph_space(placeholder, after_pt=8)
            ph_run = placeholder.runs[0]
            ph_run.italic = True
            ph_run.font.color.rgb = RGBColor(0x99, 0x99, 0x99)

    return doc


# ---------------------------------------------------------------------------
# Argument parser
# ---------------------------------------------------------------------------

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Reise-PDF aus sights.json + tagesplan.json erstellen."
    )
    parser.add_argument("--ziel", required=True,
                        help="Reiseziel Anzeigename (z.B. 'Paris')")
    parser.add_argument("--sights", required=True,
                        help="Pfad zur sights.json")
    parser.add_argument("--tagesplan", required=True,
                        help="Pfad zur tagesplan.json")
    return parser.parse_args()


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    args = parse_args()

    # --- Validate input files ---
    if not os.path.isfile(args.sights):
        print(f"❌ Fehler: sights.json nicht gefunden: {args.sights}")
        sys.exit(1)

    if not os.path.isfile(args.tagesplan):
        print(f"❌ Fehler: tagesplan.json nicht gefunden: {args.tagesplan}")
        sys.exit(1)

    # --- Load JSON ---
    try:
        with open(args.sights, "r", encoding="utf-8") as f:
            sights = json.load(f)
    except json.JSONDecodeError as e:
        print(f"❌ Fehler: sights.json hat kein gültiges JSON-Format: {e}")
        sys.exit(1)

    try:
        with open(args.tagesplan, "r", encoding="utf-8") as f:
            tagesplan = json.load(f)
    except json.JSONDecodeError as e:
        print(f"❌ Fehler: tagesplan.json hat kein gültiges JSON-Format: {e}")
        sys.exit(1)

    # --- Validate logo ---
    logo_path = os.path.join(SCRIPT_DIR, "template", "word", "media", "image1.png")
    # Resolve relative to project root (one level up from equipment/)
    if not os.path.isfile(logo_path):
        # Try one level up (project root / template/...)
        project_root = os.path.dirname(SCRIPT_DIR)
        logo_path = os.path.join(project_root, "template", "word", "media", "image1.png")

    if not os.path.isfile(logo_path):
        print(f"❌ Fehler: Logo nicht gefunden: {logo_path}")
        sys.exit(1)

    # --- Determine output paths (CWD, not script dir) ---
    ziel_normalized = normalize_ziel(args.ziel)
    cwd = os.getcwd()
    docx_filename = f"BR-REISE-{args.ziel.replace(' ', '-')}_Garamond_4_.docx"
    pdf_filename  = f"BR-REISE-{args.ziel.replace(' ', '-')}.pdf"

    # Normalize the display name part of the filename the same way
    # Spec: [ZIELORT] = normalized (spaces→hyphens etc.) but display name is preserved in the
    # Ziel argument so we build the filename directly from normalized ziel.
    # Re-read spec: "BR-REISE-[ZIELORT]" where ZIELORT is normalized.
    docx_filename = f"BR-REISE-{ziel_normalized}_Garamond_4_.docx"
    pdf_filename  = f"BR-REISE-{ziel_normalized}.pdf"

    docx_path = os.path.join(cwd, docx_filename)
    pdf_path  = os.path.join(cwd, pdf_filename)

    # --- Build DOCX ---
    doc = build_document(
        ziel=args.ziel,
        sights=sights,
        tagesplan=tagesplan,
        logo_path=logo_path,
    )
    doc.save(docx_path)
    print(f"✅ DOCX erstellt: {docx_filename}")

    # --- Convert to PDF ---
    try:
        from docx2pdf import convert
        convert(docx_path, pdf_path)
    except Exception as e:
        print(f"❌ Fehler bei der PDF-Konvertierung: {e}")
        sys.exit(1)

    print(f"✅ PDF erstellt: {pdf_filename}")
