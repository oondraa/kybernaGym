# kybernaGym

Přehled obsazenosti školní posilovny (místnost P0) podle rozvrhu SIS. Skládá se ze dvou částí:

- **Python pipeline** (`scripts/extract_schedule.py`) – stáhne obrázky rozvrhu ze SIS, vytěží OCR obsazenost místnosti P0 a uloží `web/data/schedule.json`.
- **Statický web** (`web/`) – čte `web/data/schedule.json` a zobrazuje aktuální i denní stav posilovny.

## Aktualizace dat

Automaticky přes GitHub Actions (`.github/workflows/update-schedule.yml`) – běží 4x denně (3:00, 6:00, 12:00, 18:00 Europe/Prague), stáhne aktuální rozvrh a commitne `web/data/schedule.json`, pokud se změnil.

Ruční/lokální spuštění:

```bash
pip install -r requirements.txt
python scripts/extract_schedule.py
```

Vyžaduje nainstalovaný [Tesseract OCR](https://github.com/UB-Mannheim/tesseract/wiki) (na Linuxu/CI stačí `apt install tesseract-ocr`, hledá se v `PATH`). Na Windows se použije `C:\Program Files\Tesseract-OCR\tesseract.exe`, pokud existuje, jinak lze cestu předat přes `--tesseract`. Přepínač `--no-download` přeskočí stahování a použije obrázky, co už jsou v `stazene_rozvrhy/`.

## Nasazení webu

Statický obsah je ve složce `web/` – žádný build krok. Nasazeno přes Cloudflare Pages (build output directory: `web`).
