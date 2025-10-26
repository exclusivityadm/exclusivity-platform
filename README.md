# Exclusivity — Production Build (FastAPI + Next.js)

This bundle is ready for **Python 3.13.x** and **Next.js 14**. Your existing `.env` and `.env.local` work as-is.

## Quick Start (Local)

### Backend
```bash
cd backend
python -m venv venv
# Windows PowerShell
.\venv\Scripts\Activate.ps1
pip install --upgrade pip
pip install -r requirements.txt
uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000
```
Open http://127.0.0.1:8000/docs

### Frontend
```bash
cd frontend
npm i
npm run dev
```
Open http://127.0.0.1:3000

## Render (Backend)
- Build Command: `pip install -r backend/requirements.txt`
- Start Command: `uvicorn backend.main:app --host 0.0.0.0 --port $PORT`

## Vercel (Frontend)
- Root directory: `frontend`
- Build Command: (default) `next build`
- Env Vars: copy from `frontend/.env.local` (NEXT_PUBLIC_* only)
