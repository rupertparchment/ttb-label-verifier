# TTB Label Verifier

AI-powered proof-of-concept for comparing alcohol beverage label artwork against COLA application data. Built for the TTB Compliance Division take-home exercise.

**Repository:** https://github.com/rupertparchment/ttb-label-verifier  
**Live demo:** _(deploy URL — see Deployment section below)_

## What It Does

1. Accepts label image uploads (single or batch)
2. Extracts text from the label using OCR (Tesseract, with optional OpenAI Vision fallback)
3. Compares extracted text against application fields:
   - Brand name (fuzzy match — handles `STONE'S THROW` vs `Stone's Throw`)
   - Class/type designation
   - Alcohol content (ABV/proof numeric comparison)
   - Net contents
   - Government warning (exact text; `GOVERNMENT WARNING:` must be ALL CAPS)
4. Returns pass/fail/warning per field with processing time

## Design Decisions

### Speed (< 5 seconds per label)

Sarah's team rejected a prior pilot that took 30–40 seconds per label. This prototype uses **local Tesseract OCR** with image preprocessing (contrast enhancement, upscaling, sharpening) to stay under 5 seconds on typical label images. Batch requests run in parallel via a thread pool.

Optional `OPENAI_API_KEY` enables Vision API fallback only when Tesseract confidence is low — useful for glare/angle photos Jenny mentioned, without adding latency to the common case.

### UX for non-technical agents

Dave and half the team are over 50 with varying tech comfort. The UI uses:
- Large 18px base font, high-contrast colors
- Two clear tabs: Single Label / Batch Upload
- Obvious drag-and-drop upload zone
- Green/red pass/fail badges — no hunting for results
- Expandable detail panels for agents who want to see OCR text

### Matching nuance

Dave's `STONE'S THROW` vs `Stone's Throw` scenario is handled with fuzzy brand matching (rapidfuzz token-set ratio ≥ 80%). Government warnings use strict matching per Jenny's requirement — wrong case on the header is an automatic fail.

### Out of scope (documented trade-offs)

- No COLA system integration (per Marcus — standalone PoC)
- Batch mode uses a shared application template (typical importer dump scenario); per-file JSON would be a natural next step
- No persistent storage (prototype — no PII retention concerns)
- Production would need FedRAMP/Azure deployment and on-prem OCR if outbound API calls are blocked

## Tech Stack

| Layer | Choice | Why |
|-------|--------|-----|
| Backend | Python 3.11+, FastAPI | Fast async API, good ML/OCR ecosystem |
| OCR | Tesseract + Pillow | Local, fast, no firewall issues |
| Matching | rapidfuzz | Fast fuzzy string matching |
| Frontend | React + Vite + TypeScript | Simple SPA, easy to deploy |
| Optional AI | OpenAI GPT-4o-mini Vision | Difficult image fallback |

## Prerequisites

- **Python 3.11+**
- **Node.js 18+**
- **Tesseract OCR** installed on your system:
  - Windows: `winget install UB-Mannheim.TesseractOCR` or download from [GitHub](https://github.com/UB-Mannheim/tesseract/wiki)
  - macOS: `brew install tesseract`
  - Linux: `sudo apt install tesseract-ocr`

## Setup & Run

### Backend

```bash
cd backend
python -m venv .venv

# Windows
.venv\Scripts\activate

# macOS/Linux
source .venv/bin/activate

pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

Optional: set `OPENAI_API_KEY` for Vision fallback on poor-quality images.

### Frontend

```bash
cd frontend
npm install
npm run dev
```

Open http://localhost:5173 — the Vite dev server proxies `/api` to the backend.

### Generate Sample Labels

```bash
python scripts/generate_sample_labels.py
```

Creates test labels in `sample_labels/` including pass, fuzzy-match, wrong-warning, and ABV-mismatch cases. See `sample_labels/manifest.json` for expected results.

## API

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/health` | GET | Health check |
| `/api/verify` | POST | Single label (multipart: `image` + form fields) |
| `/api/verify/batch` | POST | Batch (multipart: `images[]` + `applications_json`) |

Interactive docs at http://localhost:8000/docs when the backend is running.

## Deployment

### Recommended: Railway or Render (full stack)

1. Push repo to GitHub
2. Deploy backend service with `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
3. Add Tesseract to build (Dockerfile included)
4. Deploy frontend to Vercel/Netlify with `VITE_API_URL=https://your-api.railway.app`

### Docker

```bash
docker compose up --build
```

Serves the app at http://localhost:8080.

## Project Structure

```
ttb-label-verifier/
├── backend/
│   ├── app/
│   │   ├── main.py       # FastAPI routes
│   │   ├── ocr.py        # Image preprocessing + OCR
│   │   ├── matcher.py    # Field verification logic
│   │   ├── models.py     # Pydantic schemas
│   │   └── constants.py  # TTB warning text
│   └── requirements.txt
├── frontend/             # React UI
├── sample_labels/        # Generated test images
├── scripts/              # Label generator
├── Dockerfile
├── docker-compose.yml
└── README.md
```

## Author

Rupert Parc — TTB IT Specialist take-home submission
