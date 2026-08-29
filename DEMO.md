# Night Desk — ~4 minute demo script

Record unedited. Show the guard holding. Then show GCP.

## 0:00–0:40 · Problem

Talk over the console with seeded hold receipts already on the rows.

> Overnight review dump: refunds, loyalty farms, card testing, a traveler. The failure mode is closing money because a model felt sure. Night Desk does not close. It stamps a hold receipt.

Do not say the pile will shrink. Do not preview an inbox of two.

## 0:40–1:00 · Value

> Gemini writes the note. `decide()` stamps HOLD or ESCALATE. If Gemini, Vertex, or Pub/Sub is down, everything HOLDs. First-open is that receipt — why, present, missing — still on the row. No Vertex call to see it.

Point at the rail badges (vertex missing / pubsub missing on a local box). Point at **live shifts off**.

## 1:00–2:30 · Receipts (no stamp click)

1. Open any row. Read **why** and **present / missing** without leaving the pile.
2. Open `CASE-2404` (Tokyo traveler). It is still here. Receipt is HOLD. That is success.
3. Open a slam-dunk row (`CASE-2409` ATO). Seeded rails are down, so it is HOLD too — the punchline. Gemini never AUTO_CLOSE.
4. There is no button that starts Vertex on the public desk.

If an operator later sets `SHIFT_TOKEN` and curls `POST /api/shifts` with `X-Shift-Token`, slam-dunks may show ESCALATE when rails are up. Still no close. Nobody disappears.

## 2:30–3:40 · Proof of Google Cloud

1. Cloud Run service `nightdesk`, `*.run.app`.
2. `/api/health` — `model: gemini-3.5-flash`, rails present/missing, `shifts.enabled: false`, store firestore.
3. Firestore `nightdesk` cases/shifts.
4. Pub/Sub `nightdesk-shifts` **or** say the missing pubsub rail is why every receipt HOLDs.

> Demo runtime is Gemini 3.5, ADK, Cloud Run, Firestore, Pub/Sub. Min instances zero.

## 3:40–4:00 · Close

Stay on a HOLD row.

> The guard held. Why and present/missing are on the receipt. Gemini does not close money.

Stop.

## Prep

- [ ] First-open already shows receipts — do not click a live-shift button (there isn't one)
- [ ] GCP tab ready if you have a live deploy; otherwise show `/api/health` rails.missing
- [ ] Delete Cloud Run after the take
