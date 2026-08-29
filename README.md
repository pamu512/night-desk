# Night Desk

Hold receipts for refund, loyalty, and payment-abuse review. Two-way only: **HOLD** or **ESCALATE**. Money is never closed unattended.

**Demo runtime is Gemini 3.5 + ADK + GCP; Night Desk is a transferable skill on the buyer’s BYOM/VPC — not a hosted agent seat or a case CRM.**

**Track:** Taskmaster · **License:** Apache-2.0

You give it a goal. It gathers device / loyalty / velocity context. Gemini (when the rail is up) writes a draft note. `decide()` stamps the receipt: `{HOLD|ESCALATE}: {reason}`, evidence = the facts that fired (device_ring, bonuses, fails/BINs, INR+POD, ATO). If Gemini, Vertex, or Pub/Sub is down, every case **HOLD**s. First-open is that receipt — why + present/missing — still on the row. Nothing leaves the pile.

![Architecture](docs/architecture.svg)

## Who it's for

Fraud ops on a consumer wallet or loyalty program. Sample tenant: **Meridian Wallet**. The chore is the overnight `REVIEW` dump. The product is a guard that holds, not a shrinking inbox.

## How it works

1. A goal starts a shift (`POST /api/shifts`). Ingest goes to **Cloud Pub/Sub** when that rail is up.
2. **Google ADK** + **Gemini 3.5 Flash** write the note only. They do not close money.
3. Tools pull case file, account, device graph, velocity, loyalty, delivery / travel / ATO.
4. `decide()` is two-way. Slam-dunk abuse → `ESCALATE`. Everything else → `HOLD`.
5. Missing Gemini (or Vertex, if that is the model rail) or Pub/Sub → fail-closed `HOLD`. Never silent deny.
6. If Gemini’s draft disagrees, the receipt shows the override. The stamp wins.
7. Firestore on Cloud Run (file store locally without ADC). Console streams the trace.

### Dispositions

| Outcome | When |
|---|---|
| `ESCALATE` | Rails up **and** ATO + refund, card-testing burst, same-device refund ring, loyalty farm, or INR vs proof of delivery |
| `HOLD` | Thin/mixed evidence, household pooling, high-value without a slam-dunk — **or any rail down** |

There is no close path.

## Architecture

```
Ops console (Next.js) ──► FastAPI on Cloud Run
                              │
                              ├─ Google ADK + Gemini 3.5 Flash  (note only)
                              ├─ decide()  HOLD | ESCALATE
                              ├─ Cloud Firestore  (cases, receipts, shifts)
                              └─ Cloud Pub/Sub    (shift-started; down → HOLD)
```

Diagram: [`docs/architecture.svg`](docs/architecture.svg).

### Required stack (hackathon)

| Requirement | What Night Desk uses |
|---|---|
| Gemini 3.5 or newer | `GEMINI_MODEL=gemini-3.5-flash` via Gemini API or Vertex AI |
| Google agent framework | **Google ADK** (`google.adk.agents.llm_agent.Agent`) |
| Google Cloud service | **Firestore** + **Pub/Sub**, imported and called; deploy on **Cloud Run** |

## How to run locally

Python 3.11+ and Node 20+. No secrets. Locally Gemini and Pub/Sub are missing → every receipt is fail-closed HOLD. That is the demo.

```bash
cp .env.example .env

python3 -m venv .venv
source .venv/bin/activate
pip install -r backend/requirements.txt

# terminal 1 — API on :43148
PYTHONPATH=backend python -m nightdesk

# terminal 2 — console on :43147
cd web && npm install && npm run dev -- --port 43147
```

Open [http://127.0.0.1:43147](http://127.0.0.1:43147). Click **Stamp receipts**. Read HOLD + why + present/missing on the row. `CASE-2404` is still there.

```bash
PYTHONPATH=backend python -m nightdesk &
curl -s http://127.0.0.1:43148/api/health
curl -s -X POST http://127.0.0.1:43148/api/shifts \
  -H 'content-type: application/json' \
  -d '{"goal":"Stamp hold receipts. Never close money.","force_mock":true}'
```

### Tests

```bash
source .venv/bin/activate
PYTHONPATH=backend pytest backend/tests -q
```

Proves `decide()` cannot close, fail-closed HOLD on missing rails, and the note stamp.

### ADK web (optional)

```bash
cd backend
adk web --port 43149
```

### Docker

```bash
docker compose up --build
```

Serves API + static console on `43148`.

## Deploy to Cloud Run

Project in this write-up: `tarka-505801` (GCP project id). Do not bake keys.

```bash
export PROJECT_ID=tarka-505801
export REGION=us-central1

gcloud config set project $PROJECT_ID
gcloud services enable run.googleapis.com firestore.googleapis.com pubsub.googleapis.com aiplatform.googleapis.com

gcloud firestore databases create --location=$REGION || true
gcloud pubsub topics create nightdesk-shifts || true

echo -n "$GOOGLE_API_KEY" | gcloud secrets create gemini-api-key --data-file=- || true

gcloud run deploy nightdesk \
  --source . \
  --region $REGION \
  --allow-unauthenticated \
  --min-instances 0 \
  --max-instances 2 \
  --set-env-vars "GOOGLE_CLOUD_PROJECT=$PROJECT_ID,GEMINI_MODEL=gemini-3.5-flash,PUBSUB_TOPIC=nightdesk-shifts,GOOGLE_GENAI_USE_VERTEXAI=false" \
  --set-secrets "GOOGLE_API_KEY=gemini-api-key:latest"
```

Scale to zero. After a live GCP proof, delete the service.

Vertex path: `GOOGLE_GENAI_USE_VERTEXAI=true` and `roles/aiplatform.user` on the runtime SA. If Vertex is down, HOLD.

## Environment variables

| Variable | Purpose |
|---|---|
| `GOOGLE_API_KEY` / `GEMINI_API_KEY` | Gemini API (AI Studio) |
| `GEMINI_MODEL` | Default `gemini-3.5-flash` |
| `GOOGLE_GENAI_USE_VERTEXAI` | `true` to use Vertex |
| `GOOGLE_CLOUD_PROJECT` | GCP project |
| `GOOGLE_CLOUD_LOCATION` | Vertex / Cloud Run region |
| `GOOGLE_APPLICATION_CREDENTIALS` | ADC JSON |
| `FIRESTORE_EMULATOR_HOST` | Firestore emulator |
| `PUBSUB_EMULATOR_HOST` | Pub/Sub emulator |
| `PUBSUB_TOPIC` | Default `nightdesk-shifts` |
| `NEXT_PUBLIC_API_URL` | Console → API |

## Repository map

```
sample_data/cases.json     sample overnight cases (no secrets)
backend/nightdesk/         FastAPI + ADK + decide() + Firestore/Pub/Sub
backend/tests/             cannot-close, fail-closed, note stamp
web/                       hold-receipt console
docs/architecture.svg
DEMO.md
Dockerfile
```

## What this is not

Not a case CRM. Not a hosted agent seat. Not a close-the-queue toy. Demo runtime is Gemini 3.5 + ADK + GCP; the skill transfers onto the buyer’s model and VPC.
