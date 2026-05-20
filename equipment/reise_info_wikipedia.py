#!/usr/bin/env python3
"""
Equipment: reise_info_wikipedia.py
Zweck: Top-5 Sehenswürdigkeiten für ein Reiseziel via Wikipedia Geosearch ermitteln
       und je ein Bild herunterladen. Ergebnis als JSON speichern.
Aufruf:
  Normal:  python equipment/reise_info_wikipedia.py --ziel "Paris"
  Ersetzen: python equipment/reise_info_wikipedia.py --ziel "Paris" --replace 3 "Versailles"
"""

import argparse
import json
import os
import sys

import requests

WIKIPEDIA_API = "https://de.wikipedia.org/w/api.php"
HEADERS = {"User-Agent": "BelahmerReisen-CommandCenter/1.0 (info@belahmer-reisen.de)"}
PLACEHOLDER_NAME = "no_image.jpg"


# ---------------------------------------------------------------------------
# Hilfsfunktionen
# ---------------------------------------------------------------------------

def normalize_ziel(ziel: str) -> str:
    """Zielort in einen dateisystemfreundlichen Ordnernamen umwandeln."""
    table = str.maketrans({"ä": "ae", "ö": "oe", "ü": "ue", "ß": "ss",
                            "Ä": "ae", "Ö": "oe", "Ü": "ue"})
    normalized = ziel.translate(table)
    normalized = normalized.lower().replace(" ", "-")
    return normalized


def api_get(params: dict) -> dict:
    """Einzelne Wikipedia-API-Anfrage; bei Netzwerkfehler: Fehler ausgeben + exit(1)."""
    try:
        response = requests.get(WIKIPEDIA_API, params=params, headers=HEADERS, timeout=15)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as exc:
        print(f"❌ Netzwerkfehler: {exc}")
        sys.exit(1)


# ---------------------------------------------------------------------------
# Wikipedia-Abfragen
# ---------------------------------------------------------------------------

def get_coordinates(ziel: str) -> tuple[float, float]:
    """Koordinaten des Zielorts aus Wikipedia holen."""
    data = api_get({
        "action": "query",
        "titles": ziel,
        "prop": "coordinates",
        "format": "json",
    })
    pages = data.get("query", {}).get("pages", {})
    for page in pages.values():
        coords = page.get("coordinates", [])
        if coords:
            return coords[0]["lat"], coords[0]["lon"]
    print(f"❌ Fehler: Koordinaten für '{ziel}' nicht in Wikipedia gefunden.")
    sys.exit(1)


def geosearch_nearby(lat: float, lng: float, limit: int = 20) -> list[str]:
    """Geosearch – gibt Liste von Seitentiteln zurück."""
    data = api_get({
        "action": "query",
        "list": "geosearch",
        "gscoord": f"{lat}|{lng}",
        "gsradius": 10000,
        "gslimit": limit,
        "format": "json",
    })
    results = data.get("query", {}).get("geosearch", [])
    return [entry["title"] for entry in results]


def get_thumbnail_url(title: str) -> str | None:
    """Thumbnail-URL (800px) für einen Wikipedia-Artikeltitel holen."""
    data = api_get({
        "action": "query",
        "titles": title,
        "prop": "pageimages",
        "pithumbsize": 800,
        "format": "json",
    })
    pages = data.get("query", {}).get("pages", {})
    for page in pages.values():
        thumb = page.get("thumbnail", {})
        if thumb:
            return thumb.get("source")
    return None


# ---------------------------------------------------------------------------
# Bild-Download
# ---------------------------------------------------------------------------

def download_image(url: str, dest_path: str) -> bool:
    """Bild von URL herunterladen und unter dest_path speichern."""
    try:
        response = requests.get(url, headers=HEADERS, timeout=30, stream=True)
        response.raise_for_status()
        with open(dest_path, "wb") as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)
        return True
    except requests.exceptions.RequestException as exc:
        print(f"  ⚠️ Bild konnte nicht heruntergeladen werden: {exc}")
        return False


# ---------------------------------------------------------------------------
# Normalmodus
# ---------------------------------------------------------------------------

def run_normal(ziel: str, folder: str) -> None:
    """Top-5-Sehenswürdigkeiten ermitteln, Bilder herunterladen, JSON speichern."""
    os.makedirs(folder, exist_ok=True)

    print(f"🔍 Suche Koordinaten für '{ziel}' …")
    lat, lng = get_coordinates(ziel)
    print(f"   📍 Koordinaten: {lat}, {lng}")

    print("🔍 Geosearch – nahegelegene Sehenswürdigkeiten …")
    titles = geosearch_nearby(lat, lng)
    if not titles:
        print("❌ Fehler: Keine Sehenswürdigkeiten via Geosearch gefunden.")
        sys.exit(1)

    top5 = titles[:5]
    sights = []

    for idx, title in enumerate(top5, start=1):
        image_path = os.path.join(folder, f"sight_{idx}.jpg")
        print(f"  [{idx}/5] {title} …")
        thumb_url = get_thumbnail_url(title)
        if thumb_url:
            success = download_image(thumb_url, image_path)
            if not success:
                image_path = PLACEHOLDER_NAME
        else:
            print(f"       ⚠️ Kein Bild gefunden – Platzhalter wird verwendet.")
            image_path = PLACEHOLDER_NAME
        # Use forward slashes for cross-platform JSON compatibility
        sights.append({"name": title, "image": image_path.replace(os.sep, "/")})

    json_path = os.path.join(folder, "sights.json")
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(sights, f, ensure_ascii=False, indent=2)

    print(f"\n✅ Sights für {ziel} gespeichert: {json_path}")
    for i, s in enumerate(sights, start=1):
        print(f"{i}. {s['name']}")


# ---------------------------------------------------------------------------
# Ersetzungsmodus
# ---------------------------------------------------------------------------

def run_replace(ziel: str, folder: str, position: int, new_name: str) -> None:
    """Einen Eintrag in sights.json durch eine neue Sehenswürdigkeit ersetzen."""
    json_path = os.path.join(folder, "sights.json")
    if not os.path.exists(json_path):
        print(f"❌ Fehler: {json_path} nicht gefunden. Bitte zuerst Normalmodus ausführen.")
        sys.exit(1)

    with open(json_path, "r", encoding="utf-8") as f:
        sights = json.load(f)

    if not (1 <= position <= 5):
        print("❌ Fehler: Position muss zwischen 1 und 5 liegen.")
        sys.exit(1)

    idx = position - 1  # 0-basiert
    image_path = os.path.join(folder, f"sight_{position}.jpg")

    print(f"🔄 Ersetze Position {position}: '{sights[idx]['name']}' → '{new_name}' …")
    thumb_url = get_thumbnail_url(new_name)
    if thumb_url:
        success = download_image(thumb_url, image_path)
        if not success:
            image_path = PLACEHOLDER_NAME
    else:
        print(f"  ⚠️ Kein Bild für '{new_name}' gefunden – Platzhalter wird verwendet.")
        image_path = PLACEHOLDER_NAME

    sights[idx] = {"name": new_name, "image": image_path.replace(os.sep, "/")}

    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(sights, f, ensure_ascii=False, indent=2)

    print(f"\n✅ Sights für {ziel} aktualisiert: {json_path}")
    for i, s in enumerate(sights, start=1):
        print(f"{i}. {s['name']}")


# ---------------------------------------------------------------------------
# Argument-Parser
# ---------------------------------------------------------------------------

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Top-5 Sehenswürdigkeiten für ein Reiseziel via Wikipedia ermitteln."
    )
    parser.add_argument(
        "--ziel",
        required=True,
        help="Reiseziel (z. B. 'Paris')",
    )
    parser.add_argument(
        "--replace",
        metavar="N",
        type=int,
        choices=range(1, 6),
        help="Position (1–5) ersetzen",
    )
    parser.add_argument(
        "new_name",
        nargs="?",
        default=None,
        help="Neuer Name der Sehenswürdigkeit (nur bei --replace benötigt)",
    )
    return parser.parse_args()


# ---------------------------------------------------------------------------
# Einstiegspunkt
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    args = parse_args()

    ziel_normalized = normalize_ziel(args.ziel)
    folder = os.path.join("temp", f"reise-{ziel_normalized}")

    if args.replace is not None:
        if not args.new_name:
            print("❌ Fehler: Bei --replace muss ein neuer Name als positionales Argument angegeben werden.")
            sys.exit(1)
        run_replace(args.ziel, folder, args.replace, args.new_name)
    else:
        run_normal(args.ziel, folder)
