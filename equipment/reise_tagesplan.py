#!/usr/bin/env python3
"""
Equipment: reise_tagesplan.py
Zweck:  Tagesprogramm für eine Tagesreise berechnen – 5 Sehenswürdigkeiten aus
        sights.json gleichmäßig auf die verfügbare Zeit verteilen.
        Ergebnis als JSON (tagesplan.json) speichern.
Aufruf:
  python equipment/reise_tagesplan.py \\
      --ziel "Paris" \\
      --ankunft "11:00" \\
      --abfahrt "20:30" \\
      --heimatort "Völklingen" \\
      --heimankunft "02:30" \\
      --json "equipment/temp/reise-paris/sights.json" \\
      --aktivitaeten "equipment/temp/reise-paris/aktivitaeten.json"
"""

import argparse
import json
import os
import sys
import unicodedata
from datetime import datetime, timedelta

# Anchor temp folder to the script's own directory, not CWD
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

# Time format used throughout
TIME_FMT = "%H:%M"

# Scheduling constants (in minutes)
ANKUNFT_PAUSE = 30       # "Arrival pause" after arrival
ABFAHRT_PUFFER = 30      # Gather-before-departure buffer
BUFFER_BETWEEN = 15      # Gap between programme points
MIN_PER_SIGHT = 30       # Minimum time per sight
MAX_PER_SIGHT = 120      # Maximum time per sight
TARGET_SIGHTS = 5        # Fixed target number of sights to schedule


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def normalize_ziel(ziel: str) -> str:
    """Convert destination name to filesystem-friendly folder name.

    Applies NFKD decomposition to handle non-German special chars (é, ñ, ç …),
    strips combining characters, maps German umlauts, lowercases, and replaces
    spaces with hyphens.
    """
    decomposed = unicodedata.normalize("NFKD", ziel)
    no_accents = "".join(ch for ch in decomposed if unicodedata.category(ch) != "Mn")
    umlaut_table = str.maketrans({"ä": "ae", "ö": "oe", "ü": "ue", "ß": "ss",
                                   "Ä": "ae", "Ö": "oe", "Ü": "ue"})
    normalized = no_accents.translate(umlaut_table)
    return normalized.lower().replace(" ", "-")


def parse_time(s: str, arg_name: str) -> datetime:
    """Parse HH:MM string; exit 1 with clear error on failure."""
    try:
        return datetime.strptime(s.strip(), TIME_FMT)
    except ValueError:
        print(f"❌ Fehler: Ungültiges Zeitformat für --{arg_name}: '{s}' (erwartet HH:MM)")
        sys.exit(1)


def fmt_time(dt: datetime) -> str:
    """Format datetime as HH:MM string."""
    return dt.strftime(TIME_FMT)


def is_lunch_overlap(start: datetime, end: datetime) -> bool:
    """Return True if the slot overlaps with the 12:00–14:00 lunch window."""
    lunch_start = start.replace(hour=12, minute=0)
    lunch_end = start.replace(hour=14, minute=0)
    return start < lunch_end and end > lunch_start


def load_aktivitaeten(path: str | None) -> dict:
    """Load aktivitaeten.json if path is given and file exists.

    Returns a dict with keys 'ankunft', 'sights', and optionally 'optional'.
    Falls back to empty lists if path is None or file does not exist.
    """
    empty = {"ankunft": [], "sights": []}

    if not path:
        print("ℹ️  --aktivitaeten nicht angegeben – leere Aktivitätenlisten werden verwendet.")
        return empty

    if not os.path.exists(path):
        print(f"ℹ️  aktivitaeten.json nicht gefunden ({path}) – leere Listen werden verwendet.")
        return empty

    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)

    print(f"✅ aktivitaeten.json geladen: {path}")
    return data


# ---------------------------------------------------------------------------
# Core calculation
# ---------------------------------------------------------------------------

def calculate_tagesplan(
    ziel: str,
    ankunft: datetime,
    abfahrt: datetime,
    heimatort: str,
    heimankunft: datetime | None,
    sights: list[dict],
    aktivitaeten: dict,
) -> dict:
    """Build the structured day plan dict.

    Scheduling maths
    ----------------
    available = (abfahrt - ankunft) - ANKUNFT_PAUSE - ABFAHRT_PUFFER
    net_time  = (available - (n_sights - 1) * BUFFER_BETWEEN) / n_sights
    net_time  clipped to [MIN_PER_SIGHT, MAX_PER_SIGHT]

    If even MIN_PER_SIGHT x n_sights + (n_sights - 1) x BUFFER_BETWEEN
    exceeds available time, n_sights is reduced until it fits (warns user).
    """
    total_available = int((abfahrt - ankunft).total_seconds() // 60) \
                      - ANKUNFT_PAUSE - ABFAHRT_PUFFER

    # Guard: window too short for any programme at all
    if total_available <= 0:
        print("❌ Die Zeit zwischen Ankunft und Abfahrt ist zu kurz für eine Pause "
              "(mind. 60 Min. nötig)")
        sys.exit(1)

    # Determine how many sights actually fit
    n_sights = min(TARGET_SIGHTS, len(sights))
    while n_sights > 0:
        needed = MIN_PER_SIGHT * n_sights + BUFFER_BETWEEN * (n_sights - 1)
        if total_available >= needed:
            break
        n_sights -= 1

    if n_sights == 0:
        print("⚠️  Warnung: Verfügbare Zeit reicht für keine einzige Sehenswürdigkeit.")
    elif n_sights < TARGET_SIGHTS:
        print(f"⚠️  Warnung: Verfügbare Zeit reicht nur für {n_sights} Sehenswürdigkeit(en) "
              f"(statt {TARGET_SIGHTS}).")

    # Calculate minutes per sight
    if n_sights > 0:
        net_time = (total_available - BUFFER_BETWEEN * (n_sights - 1)) // n_sights
        net_time = max(MIN_PER_SIGHT, min(MAX_PER_SIGHT, net_time))
    else:
        net_time = 0

    # --- Aktivitaeten data ---
    ankunft_aktivitaeten = aktivitaeten.get("ankunft", [])
    sights_aktivitaeten = aktivitaeten.get("sights", [])

    # --- Build halte (sight stops) ---
    halte: list[dict] = []
    cursor = ankunft + timedelta(minutes=ANKUNFT_PAUSE)
    mittagspause_used = False

    for i in range(n_sights):
        sight = sights[i]
        sight_name = sight["name"]
        sight_image = sight.get("image", None)
        slot_start = cursor
        slot_end = cursor + timedelta(minutes=net_time)

        halt: dict = {
            "nr": i + 1,
            "name": sight_name,
            "von": fmt_time(slot_start),
            "bis": fmt_time(slot_end),
            "aktivitaeten": sights_aktivitaeten[i] if i < len(sights_aktivitaeten) else [],
            "image": sight_image,
        }

        if not mittagspause_used and is_lunch_overlap(slot_start, slot_end):
            halt["mittagspause"] = True
            mittagspause_used = True

        halte.append(halt)

        if i < n_sights - 1:
            cursor = slot_end + timedelta(minutes=BUFFER_BETWEEN)
        else:
            cursor = slot_end

    # --- Assemble top-level plan dict ---
    plan: dict = {
        "ziel": ziel,
        "ankunft": {
            "zeit": fmt_time(ankunft),
            "aktivitaeten": ankunft_aktivitaeten,
        },
        "halte": halte,
    }

    # Optional stop – only include if present in aktivitaeten.json
    optional_data = aktivitaeten.get("optional")
    if optional_data:
        plan["optional"] = {
            "name": optional_data.get("name", ""),
            "von": optional_data.get("von", ""),
            "bis": optional_data.get("bis", ""),
            "aktivitaeten": optional_data.get("aktivitaeten", []),
        }

    # Departure
    plan["abfahrt"] = {
        "zeit": fmt_time(abfahrt),
        "heimatort": heimatort,
    }

    # Home arrival – only if provided
    if heimankunft is not None:
        plan["heimankunft"] = {
            "zeit": fmt_time(heimankunft),
            "heimatort": heimatort,
        }

    return plan


# ---------------------------------------------------------------------------
# Argument parser
# ---------------------------------------------------------------------------

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Tagesprogramm für eine Tagesreise berechnen und als JSON speichern."
    )
    parser.add_argument("--ziel", required=True,
                        help="Reiseziel (Anzeigename, z. B. 'Paris')")
    parser.add_argument("--ankunft", required=True,
                        help="Ankunftszeit am Zielort (HH:MM, z. B. '11:00')")
    parser.add_argument("--abfahrt", required=True,
                        help="Abfahrtszeit vom Zielort (HH:MM, z. B. '20:30')")
    parser.add_argument("--heimatort", required=True,
                        help="Abfahrtsort für die Rückfahrt (z. B. 'Völklingen')")
    parser.add_argument("--heimankunft", default=None,
                        help="Geschätzte Heimankunftszeit (HH:MM, optional)")
    parser.add_argument("--json", required=True, dest="json_path",
                        help="Pfad zur sights.json aus Task 1")
    parser.add_argument("--aktivitaeten", default=None, dest="aktivitaeten_path",
                        help="Pfad zur aktivitaeten.json (optional)")
    return parser.parse_args()


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    args = parse_args()

    # --- Parse and validate times ---
    ankunft_dt = parse_time(args.ankunft, "ankunft")
    abfahrt_dt = parse_time(args.abfahrt, "abfahrt")

    if abfahrt_dt <= ankunft_dt:
        print(f"❌ Fehler: --abfahrt ({args.abfahrt}) muss nach --ankunft ({args.ankunft}) liegen.")
        sys.exit(1)

    heimankunft_dt = None
    if args.heimankunft:
        heimankunft_dt = parse_time(args.heimankunft, "heimankunft")
        # Fix midnight crossover: if heimankunft is on the next calendar day
        if heimankunft_dt <= abfahrt_dt:
            heimankunft_dt += timedelta(days=1)

    # --- Load sights.json ---
    if not os.path.exists(args.json_path):
        print(f"❌ Fehler: sights.json nicht gefunden: {args.json_path}")
        sys.exit(1)

    with open(args.json_path, "r", encoding="utf-8") as f:
        sights = json.load(f)

    if not sights:
        print("❌ Fehler: sights.json ist leer.")
        sys.exit(1)

    # Validate sights.json schema
    if not isinstance(sights, list) or any("name" not in entry for entry in sights):
        print("❌ Fehler: sights.json hat ein ungültiges Format")
        sys.exit(1)

    # --- Load aktivitaeten.json (optional) ---
    aktivitaeten = load_aktivitaeten(args.aktivitaeten_path)

    # --- Compute output folder (anchored to script directory) ---
    ziel_normalized = normalize_ziel(args.ziel)
    out_folder = os.path.join(SCRIPT_DIR, "temp", f"reise-{ziel_normalized}")
    os.makedirs(out_folder, exist_ok=True)
    out_path = os.path.join(out_folder, "tagesplan.json")

    # --- Build the plan ---
    plan = calculate_tagesplan(
        ziel=args.ziel,
        ankunft=ankunft_dt,
        abfahrt=abfahrt_dt,
        heimatort=args.heimatort,
        heimankunft=heimankunft_dt,
        sights=sights,
        aktivitaeten=aktivitaeten,
    )

    # --- Save JSON ---
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(plan, f, ensure_ascii=False, indent=2)

    # --- Stdout summary ---
    print(f"✅ Tagesplan für {args.ziel} erstellt: {out_path}")
    print(f"\n{'Uhrzeit':<14}| Programmpunkt")
    print(f"{'-' * 14}| {'-' * 40}")

    # Ankunft row
    print(f"{plan['ankunft']['zeit']:<14}| Ankunft in {args.ziel} & kurze Pause")

    # Sight rows
    for halt in plan["halte"]:
        zeit_display = f"{halt['von']}-{halt['bis']}"
        label = halt["name"]
        if halt.get("mittagspause"):
            label += " (Mittagspause)"
        print(f"{zeit_display:<14}| {label}")

    # Optional row (if present)
    if "optional" in plan:
        opt = plan["optional"]
        zeit_display = f"{opt['von']}-{opt['bis']}"
        print(f"{zeit_display:<14}| {opt['name']} (optional)")

    # Abfahrt row
    print(f"{plan['abfahrt']['zeit']:<14}| Abfahrt Richtung {plan['abfahrt']['heimatort']}")

    # Heimankunft row
    if "heimankunft" in plan:
        print(f"{plan['heimankunft']['zeit']:<14}| "
              f"Geplante Ankunft in {plan['heimankunft']['heimatort']}")
