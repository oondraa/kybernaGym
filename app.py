import requests
import os
from PIL import Image
import pytesseract

# 1. CESTA K TESSERACTU - Zkontroluj, jestli to tam fakt máš!
pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'

# 2. TVOJE ZMĚŘENÁ DATA
START_X = 41
START_Y = 101
CELL_W = 88
CELL_H = 43
LINE_W = 2  # Svislá čára
LINE_H = 1  # Vodorovná čára

# Uprav podle toho, kolikátý řádek je posilovna (počítej od 0 pro G1)
# Pokud je posilovna třeba 15. řádek, napiš 14 (protože programy počítají od nuly)
RADEK_POSILOVNA = 14 

CASY = [
    "07:00-07:45", "07:50-08:35", "08:45-09:30", "09:45-10:30", "10:45-11:30",
    "11:45-12:30", "12:45-13:30", "13:45-14:30", "14:45-15:30", "15:45-16:30",
    "16:45-17:30", "17:45-18:30"
]

def stahni_rozvrhy():
    dny = ['PO1', 'UT1', 'ST1', 'CT1', 'PA1']
    base_url = "https://sis.ssakhk.cz/TimeTable/"
    if not os.path.exists("stazene_rozvrhy"):
        os.makedirs("stazene_rozvrhy")
    
    headers = {'User-Agent': 'Mozilla/5.0'}
    print("--- STAHOVÁNÍ ---")
    for den in dny:
        url = f"{base_url}{den}.jpg"
        r = requests.get(url, headers=headers)
        if r.status_code == 200:
            with open(f"stazene_rozvrhy/{den}.jpg", 'wb') as f:
                f.write(r.content)
            print(f"Staženo: {den}.jpg")
        else:
            print(f"Chyba při stahování {den}: {r.status_code}")

def analyzuj_den(img_path):
    if not os.path.exists(img_path):
        return
    
    img = Image.open(img_path).convert('L')
    print(f"\n--- ANALÝZA: {img_path} ---")
    
    for i in range(12): # 0. až 11. hodina
        x_left = START_X + (i * (CELL_W + LINE_W))
        y_top = START_Y + (RADEK_POSILOVNA * (CELL_H + LINE_H))
        
        crop = img.crop((x_left, y_top, x_left + CELL_W, y_top + CELL_H))
        
        # Předzpracování: text bude černý, pozadí bílé
        crop = crop.point(lambda p: 0 if p < 160 else 255)
        
        # OCR (psm 7 znamená, že čteme jeden řádek textu)
        text = pytesseract.image_to_string(crop, config='--psm 7').strip()
        
        stav = "OBSAZENO" if len(text) > 1 else "VOLNO"
        print(f"{CASY[i]}: {stav} {f'({text})' if text else ''}")

if __name__ == "__main__":
    stahni_rozvrhy()
    # Teď zkusíme zanalyzovat pondělí
    analyzuj_den('stazene_rozvrhy/PO1.jpg')