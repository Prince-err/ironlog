# Iron Log — Deployment Handoff (for Manus)

## What this app is
Iron Log — a personal premium gym workout tracker (progressive overload, PRs, streaks).

Stack:
- `gym/backend` — **FastAPI** (Python 3.12), SQLAlchemy 2.0, SQLite (`ironlog.db`)
- `gym/frontend` — **Next.js 16** (App Router, TypeScript, Tailwind v4, React 19), a **PWA** (installable on iPhone)

## Critical architecture facts
1. The browser **never talks to FastAPI directly**. All API calls go to `/api/v1/*` on the frontend origin, which must be proxied to the backend:
   - In dev, `next.config.ts` rewrites `/api/v1/:path*` → `API_ORIGIN` (default `http://127.0.0.1:8000`).
   - In production, use `vite.config.ts`-style rewrite OR configure Next.js rewrites with `API_ORIGIN` env var, OR run behind Nginx/Caddy which proxies `/api/v1/*` to the backend and serves Next.js for everything else.
2. All frontend pages are **100% client-side** (“use client” everywhere). `next build && next start` works fine as a node server; full static export also works.
3. Dev-only identity: requests carry header `X-Demo-User-ID: 1`. Backend resolves it in `backend/app/api/deps.py` (single swap point for real auth later). For a personal single-user deployment this is acceptable; it is NOT secure for multi-user.
4. **SQLite persistence:** the DB file lives wherever `DATABASE_URL` (default `sqlite:///./ironlog.db`) points. On any containerized host the default working-dir path is **ephemeral** — mount a persistent volume and set e.g. `DATABASE_URL=sqlite:////data/ironlog.db` pointing into the mounted volume, or migrate to Postgres (SQLAlchemy config swap, models are portable).

## How to run locally (reference)
Backend:
```bash
cd gym/backend
python -m venv .venv && .venv/bin/pip install -r requirements.txt
python -m app.db.seed      # creates tables + ~170 exercises + demo user + 3 templates (NO workout history)
uvicorn app.main:app --port 8000
```
Frontend:
```bash
cd gym/frontend
npm install
npm run build
npm start   # port 3000, proxies /api/v1/* to API_ORIGIN (default 127.0.0.1:8000)
```
Health check: `GET /api/v1/health` → `{"status":"ok","service":"iron-log-api"}`

## PWA (iPhone X install)
Already configured in `frontend/app/layout.tsx` + `frontend/public/`:
- `manifest.json` (standalone, portrait, dark theme `#09090b`)
- `icon-192.png`, `icon-512.png`
- `viewportFit: cover` + safe-area insets handled in the UI (bottom nav respects notch/home indicator)
- Requires **HTTPS** for install — plain HTTP won't offer "Add to Home Screen" as PWA on iOS.

## What Manus should do (deployment options, cheapest first)
1. **Single VPS host (cheapest, simplest):** Debian box + Caddy (auto-HTTPS) proxying: `/api/v1/*` → `uvicorn` on :8000; everything else → `next start`/standalone build on :3000. Mount a volume at `/data`, set `DATABASE_URL=sqlite:////data/ironlog.db`. Run both processes under systemd or Docker Compose.
2. **Two PaaS services:** frontend on Vercel (Next.js-native), backend on Railway/Render/Fly.io with a persistent volume or Postgres. On Vercel set `API_ORIGIN` env to the backend URL — rewrites are runtime-evaluated so this works without rebuilding.
3. **Docker Compose on any cloud VM:** two containers (backend uvicorn, frontend `next start`), plus Caddy reverse proxy container for TLS.

## Tests (should pass before deploying)
- Backend: `cd gym/backend && pytest tests/ -q` → 40 tests
- Frontend: `cd gym/frontend && npm test` → 22 tests
- Typecheck: `npm run typecheck`, Lint: `npm run lint` (0 errors expected)

## Env vars
- Backend: `DATABASE_URL` (optional; defaults to local SQLite file)
- Frontend: `API_ORIGIN` (optional; backend origin behind `/api/v1/*`)
