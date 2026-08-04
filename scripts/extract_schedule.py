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

from PIL import Image
import pytesseract

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

# den v obrázku -> (zkratka dne, pořadí, popisek data - podle poslední známé edice rozvrhu)
DAYS = [
    ("PO1", "PO", "Pondělí", "20.4.2026"),
    ("UT1", "UT", "Úterý", "21.4.2026"),
    ("ST1", "ST", "Středa", "22.4.2026"),
    ("CT1", "CT", "Čtvrtek", "23.4.2026"),
    ("PA1", "PA", "Pátek", "24.4.2026"),
]

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
IMG_DIR = os.path.join(BASE_DIR, "stazene_rozvrhy")
OUT_PATH = os.path.join(BASE_DIR, "web", "data", "schedule.json")


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

    for filename, code, cz_name, date_label in DAYS:
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
            "Data vytěžena OCR z posledního dostupného rozvrhu (SIS školy je mimo "
            "provoz o prázdninách). Reálná obsazenost se může od nástupu do nového "
            "školního roku lišit."
        ),
        "times": CASY,
        "room": "P0 (posilovna)",
        "day_order": [code for _, code, _, _ in DAYS],
        "days": days_out,
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--tesseract", default=r"C:\Program Files\Tesseract-OCR\tesseract.exe")
    args = parser.parse_args()

    data = build_schedule(tesseract_cmd=args.tesseract)

    os.makedirs(os.path.dirname(OUT_PATH), exist_ok=True)
    with open(OUT_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    print(f"\nHotovo. Uloženo do {OUT_PATH}")


if __name__ == "__main__":
    main()
