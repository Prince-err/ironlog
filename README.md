# Iron Log — Gym Workout Tracker

A fast, minimal, premium gym tracker focused on **progressive overload**,
workout history, consistency and simple daily execution.

Stack: **Next.js (TypeScript, App Router, Tailwind v4) → FastAPI → SQLite**

```text
OPEN APP → SEE TODAY'S MISSION → START WORKOUT → LOG SETS
→ SEE PREVIOUS PERFORMANCE → GET PROGRESSIVE OVERLOAD SUGGESTION
→ FINISH WORKOUT → STREAK + PRs + GRAPHS UPDATE
```

## Feature map (vs. product spec)

| Spec section | Where it lives |
|---|---|
| §2 Exercise database (~170 exercises, expandable) | `backend/app/db/exercise_data.py`, custom exercises via `POST /api/v1/exercises` |
| §3 Exercise type system (bodyweight / free weight / machine / cable / duration) | `Exercise.resistance` + per-set questions in the logger |
| §4 Workout logging with previous performance | `components/workout/SetLogger.tsx` |
| §5 Progressive overload engine | `backend/app/services/overload.py` |
| §6 Exercise history + filters | `GET /exercises/{id}/history?range=…`, `/exercises/[id]` page |
| §7 Progress graphs (weight/reps/volume/e1RM/sets, hover) | `components/charts/LineChart.tsx` |
| §8 Personal records (8 categories) | `backend/app/services/prs.py`, `/history/prs` |
| §9/§22 Dashboard + heatmap | `components/dashboard/DashboardView.tsx` |
| §10 Streaks (rest-day tolerant) + calendar heatmap | `backend/app/services/streaks.py`, dashboard heatmap |
| §11 Daily missions | `backend/app/services/missions.py` |
| §12 Workout templates + drag & drop | `backend/app/services/templates.py`, reordering API |
| §13 Repeat last workout (prefill, never auto-submit) | `GET /templates/{id}/previous` snapshot |
| §14 Exercise detail page | `/exercises/[id]` |
| §15 Workout summary | `components/workout/WorkoutComplete.tsx` |
| §16/§17 Analytics + muscle-group volume | `/progress`, `backend/app/services/analytics.py` |
| §18 Relational data model, sparse sets | `backend/app/models/` |
| §19 Smart bodyweight handling | separate `bodyweight` / `added_weight` columns |
| §20 Units (kg/lb) | stored in kg; display conversion in `lib/format.ts` |
| §25 Safety rules | engine never suggests aggressive jumps; est. 1RM always labelled |

## Project layout

```text
gym/
├── backend/
│   ├── app/
│   │   ├── api/routes/       # exercises, workouts, misc (dashboard/analytics/…)
│   │   ├── core/config.py
│   │   ├── db/               # session, models, seed, exercise catalog
│   │   ├── models/           # SQLAlchemy models (spec §18)
│   │   ├── schemas/          # Pydantic request bodies
│   │   └── services/         # engines: overload, prs, streaks, missions, analytics
│   ├── tests/                # pytest — 40 tests, isolated in-memory SQLite
│   └── requirements.txt
└── frontend/
    ├── app/                  # pages: /, workout, history, progress, profile
    ├── components/           # workout/, dashboard/, charts/, ui/, nav/
    └── lib/                  # api client, types, formatting
```

Architecture boundaries: **UI (frontend) → REST API → services (business logic)
→ models (database)**. All metrics, recommendations and PRs are computed from
recorded sets — the app never invents progress.

## Running locally (Windows, Git Bash / PowerShell)

### 1. Backend (first time)

```bash
cd gym/backend
python -m venv .venv
.venv/Scripts/activate          # Git Bash: source .venv/Scripts/activate
pip install -r requirements.txt
```

### 2. Seed + start FastAPI

```bash
cd gym/backend
python -m app.db.seed           # creates ironlog.db (catalog + user + templates)
.venv/Scripts/python.exe -m uvicorn app.main:app --reload --port 8000
```

Health check: <http://localhost:8000/api/v1/health> → `{"status":"ok"}`

The seed creates a demo user (id 1, `demo@ironlog.app`), the ~170-exercise
catalog and Push/Pull/Legs templates — but **no workout history**. The app
starts with a clean log, ready for real training data. (Tests build their own
fictional history via `tests/demo_history.py`.)

### 3. Frontend

```bash
cd gym/frontend
npm install
npm run dev
# http://localhost:3000  (proxies /api/v1/* to FastAPI)
```

### 4. Tests

```bash
cd gym/backend && .venv/Scripts/python.exe -m pytest tests/ -q   # 40 tests
cd gym/frontend && npm test                                      # 13 tests
npm run typecheck && npm run lint
```

Test suite runs against an **isolated in-memory SQLite** database — the dev
`ironlog.db` is never touched.

## Identity (development-only)

Like the sibling Study Command Center app, requests carry an
`X-Demo-User-ID` header resolved by `backend/app/api/deps.py`. This is a
development-only mechanism with **no security**; all routes depend on one
function so real auth is a one-file swap.

## Accuracy rules baked into the product

- Dumbbell weights are stored **per dumbbell** with total load = ×2.
- Bodyweight + added weight store **three** values: bodyweight, added
  weight, total resistance — comparable across bodyweight changes.
- A plank never stores a weight; sets are sparse by design.
- Estimated 1RM (Epley) is always labelled *estimated*, never presented as a
  measured max.
- Volume (weight × reps) is a training-load indicator, not a proxy for
  muscle growth.
- Overload suggestions can always be overridden — logging what you actually
  did is the source of truth.

## Extending later

The service-layer split leaves clean seams for: wearable/health integrations
(new ingest service), AI workout analysis (reads the same set history),
exercise videos (attachment table + exercise detail slot), nutrition and
recovery tracking (new date-keyed log models like `BodyweightLog`), coach
mode (shared user scoping). PostgreSQL is a config swap
(`DATABASE_URL=postgresql+psycopg://…`).
