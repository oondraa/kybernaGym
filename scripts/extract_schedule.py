"""
Vytáhne z obrázků rozvrhu (stazene_rozvrhy/*.jpg) obsazenost posilovny (místnost P0)
a uloží výsledek do web/data/schedule.json, který čte frontend.

Rozvrh je mřížka: řádky = skupiny (G1-G4, T1-T4, I1-I4, X3), sloupce = vyučovací hodiny.
Posilovna se v mřížce neobjevuje jako jeden pevný řádek, ale jako kód místnosti "P0"
roztroušený v různých řádkách (kdykoliv má daná skupina tělocvik v posilovně) -
proto se prohledává úplně celá mřížka, buňku po buňce.

Spuštění:
    python scripts/extract_schedule.py
Volitelně jiná cesta k tesseractu:
    python scripts/extract_schedule.py --tesseract "C:\\Program Files\\Tesseract-OCR\\tesseract.exe"
"""

import argparse
import json
import os
import sys
from datetime import datetime, timezone, timedelta
from zoneinfo import ZoneInfo

import requests
from PIL import Image
import pytesseract

SIS_BASE_URL = "https://sis.ssakhk.cz/TimeTable/"
TZ = ZoneInfo("Europe/Prague")

# --- Kalibrace mřížky (ověřeno na skutečných obrázcích) ---
START_X, START_Y = 41, 101
CELL_W, CELL_H = 88, 43
LINE_W, LINE_H = 2, 1
ROW_COUNT = 13
COL_COUNT = 12

ROW_LABELS = ["G1", "T1", "I1", "G2", "T2", "I2", "G3", "T3", "I3", "G4", "T4", "I4", "X3"]

CASY = [
    "07:00-07:45", "07:50-08:35", "08:45-09:30", "09:45-10:30", "10:45-11:30",
    "11:45-12:30", "12:45-13:30", "13:45-14:30", "14:45-15:30", "15:45-16:30",
    "16:45-17:30", "17:45-18:30",
]

# Kódy místnosti, které OCR může vyrobit z "P0" (nula se občas přečte jako písmeno O)
POSILOVNA_ROOM_CODES = {"P0", "PO"}

# den v obrázku -> (zkratka dne, pořadí, název dne, posun oproti pondělí týdne)
DAYS = [
    ("PO1", "PO", "Pondělí", 0),
    ("UT1", "UT", "Úterý", 1),
    ("ST1", "ST", "Středa", 2),
    ("CT1", "CT", "Čtvrtek", 3),
    ("PA1", "PA", "Pátek", 4),
]


BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
IMG_DIR = os.path.join(BASE_DIR, "stazene_rozvrhy")
OUT_PATH = os.path.join(BASE_DIR, "web", "data", "schedule.json")


def current_week_monday():
    """Vrátí datum pondělí aktuálního týdne (Europe/Prague) - rozvrh na
    SIS je vždy pro aktuálně probíhající školní týden."""
    today = datetime.now(TZ)
    return today - timedelta(days=today.weekday())


def download_schedules():
    """Stáhne čerstvé obrázky rozvrhu ze SIS (přepíše ty ve stazene_rozvrhy/).

    Na začátku školního roku SIS zveřejňuje rozvrh jen den (nebo pár dní)
    dopředu - obrázek pro den, který ještě není hotový, buď chybí (404),
    nebo je to prázdná mřížka. Obojí je v pořádku, extract_day() takový
    den prostě vyhodnotí jako "posilovna volná".
    """
    os.makedirs(IMG_DIR, exist_ok=True)
    headers = {"User-Agent": "Mozilla/5.0"}
    for filename, code, cz_name, _ in DAYS:
        url = f"{SIS_BASE_URL}{filename}.jpg"
        try:
            r = requests.get(url, headers=headers, timeout=15)
            r.raise_for_status()
            with open(os.path.join(IMG_DIR, f"{filename}.jpg"), "wb") as f:
                f.write(r.content)
            print(f"[stazeno] {cz_name} ({filename}.jpg)")
        except requests.RequestException as err:
            print(f"[!] Nepodařilo se stáhnout {filename}.jpg: {err}", file=sys.stderr)


def cell_box(row, col):
    x = START_X + col * (CELL_W + LINE_W)
    y = START_Y + row * (CELL_H + LINE_H)
    return (x, y, x + CELL_W, y + CELL_H)


def read_cell(img_gray, row, col):
    crop = img_gray.crop(cell_box(row, col))
    crop = crop.resize((crop.width * 3, crop.height * 3), Image.LANCZOS)
    crop = crop.point(lambda p: 0 if p < 160 else 255)
    text = pytesseract.image_to_string(crop, config="--psm 6")
    return [line.strip() for line in text.split("\n") if line.strip()]


def extract_day(img_path):
    """Vrátí pro každou periodu (0-11) seznam skupin, které mají v tu dobu posilovnu."""
    img = Image.open(img_path).convert("L")
    slots = [[] for _ in range(COL_COUNT)]

    for row in range(ROW_COUNT):
        for col in range(COL_COUNT):
            lines = read_cell(img, row, col)
            if not lines:
                continue
            room = lines[-1].strip().upper()
            if room in POSILOVNA_ROOM_CODES:
                subject = lines[0] if len(lines) > 0 else ""
                teacher = lines[1] if len(lines) > 2 else ""
                slots[col].append({
                    "group": ROW_LABELS[row],
                    "subject": subject,
                    "teacher": teacher,
                })
    return slots


def build_schedule(tesseract_cmd=None):
    if tesseract_cmd:
        pytesseract.pytesseract.tesseract_cmd = tesseract_cmd

    days_out = {}
    any_found = False
    monday = current_week_monday()

    for filename, code, cz_name, day_offset in DAYS:
        d = monday + timedelta(days=day_offset)
        date_label = f"{d.day}.{d.month}.{d.year}"
        img_path = os.path.join(IMG_DIR, f"{filename}.jpg")
        if not os.path.exists(img_path):
            print(f"[!] Přeskakuji {filename}: obrázek nenalezen ({img_path})")
            continue

        print(f"--- Analyzuji {cz_name} ({filename}.jpg) ---")
        slots = extract_day(img_path)

        day_slots = []
        for period, entries in enumerate(slots):
            occupied = len(entries) > 0
            if occupied:
                any_found = True
            day_slots.append({
                "period": period,
                "time": CASY[period],
                "occupied": occupied,
                "entries": entries,
            })
            status = "OBSAZENO" if occupied else "volno"
            who = ", ".join(e["group"] for e in entries)
            print(f"  {CASY[period]}: {status} {('(' + who + ')') if who else ''}")

        days_out[code] = {
            "name": cz_name,
            "date_label": date_label,
            "slots": day_slots,
        }

    if not any_found:
        print("\n[!] Ve všech dnech vyšla posilovna jako trvale volná - "
              "zkontroluj kalibraci mřížky (START_X/START_Y/CELL_W/CELL_H) "
              "nebo POSILOVNA_ROOM_CODES.", file=sys.stderr)

    return {
        "generated_at": datetime.now(timezone(timedelta(hours=2))).isoformat(),
        "source_note": (
            "Data vytěžena OCR z aktuálního rozvrhu SIS, automaticky aktualizováno "
            "několikrát denně."
        ),
        "times": CASY,
        "room": "P0 (posilovna)",
        "day_order": [code for _, code, _, _ in DAYS],
        "days": days_out,
    }


def main():
    default_tesseract = r"C:\Program Files\Tesseract-OCR\tesseract.exe"
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--tesseract",
        default=default_tesseract if os.path.exists(default_tesseract) else None,
        help="Cesta k tesseract.exe (na Linuxu/CI se hledá v PATH, netřeba zadávat).",
    )
    parser.add_argument(
        "--no-download",
        action="store_true",
        help="Nestahovat čerstvé obrázky ze SIS, použít jen to, co už je ve stazene_rozvrhy/.",
    )
    args = parser.parse_args()

    if not args.no_download:
        download_schedules()

    data = build_schedule(tesseract_cmd=args.tesseract)

    os.makedirs(os.path.dirname(OUT_PATH), exist_ok=True)
    with open(OUT_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    print(f"\nHotovo. Uloženo do {OUT_PATH}")


if __name__ == "__main__":
    main()
