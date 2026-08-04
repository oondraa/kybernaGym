# kybernaGym

Přehled obsazenosti školní posilovny (místnost P0) podle rozvrhu SIS. Skládá se ze dvou částí:

- **Python pipeline** (`app.py`, `scripts/extract_schedule.py`) – stáhne obrázky rozvrhu ze SIS, vytěží OCR obsazenost místnosti P0 a uloží `web/data/schedule.json`.
- **Statický web** (`web/`) – čte `web/data/schedule.json` a zobrazuje aktuální i denní stav posilovny.

## Aktualizace dat

```bash
pip install -r requirements.txt
python scripts/extract_schedule.py
```

Vyžaduje nainstalovaný [Tesseract OCR](https://github.com/UB-Mannheim/tesseract/wiki). Cestu k `tesseract.exe` lze předat přes `--tesseract`.

## Nasazení webu

Statický obsah je ve složce `web/` – žádný build krok. Nasazeno přes Cloudflare Pages (build output directory: `web`).
