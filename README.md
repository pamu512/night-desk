# Night Desk

Autonomous overnight triage for refund, loyalty, and payment-abuse queues.

**Track:** Taskmaster · **Hackathon:** [All Things Agentic](https://allthingsagentichackathon.devpost.com/) · **License:** Apache-2.0

Night Desk is a working night-shift agent, not a chatbot. You give it a goal — *clear the overnight queue, write a note on every case, leave only the real decisions for a human* — and it plans, gathers device / loyalty / velocity context, writes the case note, and applies a deterministic policy guard. The morning analyst opens an inbox of two cases, not ten.

It sits in the same domain as [Tarka](https://github.com/pamu512/tarka): local-first fraud/risk ops. Tarka evaluates. Night Desk drains the review pile the evaluate step leaves behind.

![Architecture](docs/architecture.svg)

## Who it's for

Fraud ops and risk analysts at a consumer wallet or loyalty program. The sample tenant is **Meridian Wallet** — cards, refunds, and points. The messy chore is the 02:00 dump of `REVIEW` cases: serial refunds, welcome-bonus farms, card testing, friendly-fraud INR claims, the occasional eight-year customer in Tokyo.

## How it works

1. A goal starts a shift (`POST /api/shifts`). The start is published to **Cloud Pub/Sub** (`nightdesk-shifts`).
2. The **Google ADK** shift boss (Gemini 3.5 Flash when a key is present; a tool planner otherwise) walks every `OPEN` case.
3. Tools pull the case file, account profile, device graph, auth velocity, loyalty history, and delivery / travel / ATO flags.
4. The agent writes a structured case note (summary, evidence, recommended disposition, confidence).
5. A **policy guard** — plain Python, tested, not an LLM — is the last word. Low confidence is forced to `HUMAN_QUEUE`.
6. Cases and shift state persist in **Firestore** on Cloud Run (JSON file store locally if there is no emulator or ADC).
7. The ops console streams the trace over SSE. Only `HUMAN_QUEUE` items appear in the morning inbox.

### Dispositions

| Outcome | When |
|---|---|
| `AUTO_ESCALATE` | ATO + refund, card-testing burst, same-device refund ring, loyalty farm, INR vs proof of delivery |
| `AUTO_CLOSE` | Long-tenured traveler that matches itinerary; single-PAN soft-decline retry |
| `HUMAN_QUEUE` | High-value mixed signals, household point-pooling, or writer confidence &lt; 0.72 |

Sample queue (10 cases in `sample_data/cases.json`): 6 escalate, 2 close, **2 human**. That split is the demo.

## Architecture

```
Ops console (Next.js) ──► FastAPI on Cloud Run
                              │
                              ├─ Google ADK + Gemini 3.5 Flash
                              │    tools: case, graph, velocity, loyalty, note
                              ├─ Policy guard (deterministic)
                              ├─ Cloud Firestore  (cases, notes, shifts)
                              └─ Cloud Pub/Sub    (shift-started)
```

The diagram asset lives at [`docs/architecture.svg`](docs/architecture.svg).

### Required stack (hackathon)

| Requirement | What Night Desk uses |
|---|---|
| Gemini 3.5 or newer | `GEMINI_MODEL=gemini-3.5-flash` via Gemini API or Vertex AI |
| Google agent framework | **Google ADK** (`google.adk.agents.llm_agent.Agent`) |
| Google Cloud service | **Firestore** + **Pub/Sub**, imported and called in `nightdesk/store.py` and `nightdesk/ingest.py`; deploy target is **Cloud Run** |

## How to run locally

Python 3.11+ and Node 20+. No secrets required for the sample queue — the planner uses the same tools as the Gemini agent.

```bash
cp .env.example .env
# optional, for the live ADK path:
# echo 'GOOGLE_API_KEY=your_ai_studio_key' >> .env

python3 -m venv .venv
source .venv/bin/activate
pip install -r backend/requirements.txt

# terminal 1 — API on :43148
PYTHONPATH=backend python -m nightdesk

# terminal 2 — console on :43147
cd web && npm install && npm run dev -- --port 43147
```

Open [http://127.0.0.1:43147](http://127.0.0.1:43147). Click **Run night shift**. Watch the trace. Open **Human inbox**.

One-shot API check without the UI:

```bash
PYTHONPATH=backend python -m nightdesk &
curl -s http://127.0.0.1:43148/api/health
curl -s -X POST http://127.0.0.1:43148/api/shifts \
  -H 'content-type: application/json' \
  -d '{"goal":"Clear the overnight queue.","force_mock":true}'
```

### Tests

```bash
source .venv/bin/activate
PYTHONPATH=backend pytest backend/tests -q
```

### ADK web (optional)

```bash
cd backend
adk web --port 43149
```

The `nightdesk` agent under `backend/agents/` is the same shift boss.

### Docker

```bash
docker compose up --build
```

Compose builds the static console into the API image and serves both on port `43148`.

## Deploy to Cloud Run

Project used in this write-up: `tarka-505801`. Do not bake keys into the image.

```bash
export PROJECT_ID=tarka-505801
export REGION=us-central1

gcloud config set project $PROJECT_ID
gcloud services enable run.googleapis.com firestore.googleapis.com pubsub.googleapis.com aiplatform.googleapis.com

gcloud firestore databases create --location=$REGION || true
gcloud pubsub topics create nightdesk-shifts || true

# Gemini API key as a Secret Manager secret (preferred) or --set-env-vars
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

`--source .` uses the repo `Dockerfile`. Scale-to-zero keeps spend near zero. After the demo video, delete the service:

```bash
gcloud run services delete nightdesk --region $REGION
```

Vertex path (no AI Studio key): set `GOOGLE_GENAI_USE_VERTEXAI=true` and grant the Cloud Run service account `roles/aiplatform.user`.

## Environment variables

| Variable | Purpose |
|---|---|
| `GOOGLE_API_KEY` / `GEMINI_API_KEY` | Gemini API (AI Studio) |
| `GEMINI_MODEL` | Default `gemini-3.5-flash` |
| `GOOGLE_GENAI_USE_VERTEXAI` | `true` to use Vertex |
| `GOOGLE_CLOUD_PROJECT` | GCP project (`tarka-505801`) |
| `GOOGLE_CLOUD_LOCATION` | Vertex / Cloud Run region |
| `GOOGLE_APPLICATION_CREDENTIALS` | ADC JSON (local cloud path) |
| `FIRESTORE_EMULATOR_HOST` | Use the Firestore emulator |
| `PUBSUB_EMULATOR_HOST` | Use the Pub/Sub emulator |
| `PUBSUB_TOPIC` | Default `nightdesk-shifts` |
| `NEXT_PUBLIC_API_URL` | Console → API (local default `http://127.0.0.1:43148`) |

## Repository map

```
sample_data/cases.json     10 overnight cases (no secrets)
backend/nightdesk/         FastAPI + ADK agent + policy + Firestore/Pub/Sub
backend/tests/             policy + agent loop + tools
web/                       Next.js ops console
docs/architecture.svg      diagram asset
DEMO.md                    ~4 min video script
Dockerfile                 Cloud Run image (API + static console)
```

## Demo video

See [`DEMO.md`](DEMO.md).

## What this is not

Not a replacement for Tarka's evaluate path. Not a chat window. Not a live 24/7 deployment — spin it up for the video, then scale to zero.
