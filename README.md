# TTB Label Verifier

AI-powered proof-of-concept for comparing alcohol beverage label artwork against COLA application data. Built for the TTB Compliance Division take-home exercise.

**Repository:** https://github.com/rupertparchment/ttb-label-verifier  
**Live demo:** https://ttb-label-verifier-m28m.onrender.com

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

## Assumptions & Limitations

### Assumptions

- **Application data is entered manually** (or via a shared batch template), not pulled from COLA. In production this would come from the COLA system or an importer CSV/API.
- **OCR reads the label image only.** The "expected" values always come from the application side of the comparison — the tool does not infer what the application *should* say from the label alone.
- **The sample dropdown is for demo and testing.** It pre-fills application fields for the images in `sample_labels/`; it is not a production feature.
- **Typical batch use case** is one importer submitting many labels with the same brand/format (Janet's scenario), which is why batch mode shares one application template across uploads.

### Limitations

- **No COLA integration** — standalone proof-of-concept per stakeholder guidance; authorization and FedRAMP would be a separate effort.
- **Bold government warning not verified** — Jenny noted the warning must be bold and ALL CAPS; OCR checks header casing and word-for-word text, but cannot reliably detect font weight. A vision/layout model would be needed for that.
- **Difficult photos (glare, angle, poor lighting)** — image preprocessing helps; optional OpenAI Vision fallback exists in code but is not enabled on the live demo (no API key). Agents would still reject unreadable labels today.
- **Beer/wine ABV exceptions** — matching uses generic ABV/proof parsing; beverage-type-specific TTB rules (e.g. certain wines/beers exempt from ABV display) are not implemented.
- **Batch mode lacks per-file application data** — all images in a batch are checked against the same form. Mixed-application batches would need a CSV/JSON upload (API support for `applications_json` per file is already in place).
- **No persistent storage** — uploads are processed in memory; nothing is retained after the request (appropriate for a prototype, required for production compliance).
- **Render free tier cold start** — the live demo may take 30–60 seconds to respond on first visit after idle; subsequent requests are fast.
- **No CI pipeline** — unit tests exist locally (`backend/tests/`) but are not wired to GitHub Actions.

### Natural next steps for production

- COLA API integration for application data
- Per-file batch import (CSV/JSON)
- On-prem OCR or FedRAMP-approved Azure deployment (Marcus's environment)
- Vision model for bold-text and layout validation
- Document retention and PII policies per federal requirements

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
