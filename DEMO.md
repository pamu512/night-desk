# Night Desk — ~4 minute demo script

Record unedited. Show the guard holding. Then show GCP.

## 0:00–0:40 · Problem

Talk over the console with the sample rows loaded, receipts not stamped yet.

> Overnight review dump: refunds, loyalty farms, card testing, a traveler. The failure mode is closing money because a model felt sure. Night Desk does not close. It stamps a hold receipt.

Do not say the pile will shrink. Do not preview an inbox of two.

## 0:40–1:00 · Value

> Gemini writes the note. `decide()` stamps HOLD or ESCALATE. If Gemini, Vertex, or Pub/Sub is down, everything HOLDs. First-open is that receipt — why, present, missing — still on the row.

Point at the rail badges (vertex missing / pubsub missing on a local box).

## 1:00–2:30 · Live run

1. Click **Stamp receipts**.
2. On the trace, call out fail-closed / `HOLD:` lines.
3. On the list, open any row. Read **why** and **present / missing** without leaving the pile.
4. Open `CASE-2404` (Tokyo traveler). It is still here. Receipt is HOLD. That is success.
5. Open a slam-dunk row (`CASE-2409` ATO). Locally, rails are down, so it is HOLD too — the punchline. Gemini never AUTO_CLOSE.

If rails are up on Cloud Run, slam-dunks may show ESCALATE. Still no close. Nobody disappears.

## 2:30–3:40 · Proof of Google Cloud

1. Cloud Run service `nightdesk`, `*.run.app`.
2. `/api/health` — `model: gemini-3.5-flash`, rails present/missing, store firestore.
3. Firestore `nightdesk` cases/shifts.
4. Pub/Sub `nightdesk-shifts` **or** say the missing pubsub rail is why every receipt HOLDs.

> Demo runtime is Gemini 3.5, ADK, Cloud Run, Firestore, Pub/Sub. Min instances zero.

## 3:40–4:00 · Close

Stay on a HOLD row.

> The guard held. Why and present/missing are on the receipt. Gemini does not close money.

Stop.

## Prep

- [ ] Reseed, then stamp once on camera
- [ ] GCP tab ready if you have a live deploy; otherwise show `/api/health` rails.missing
- [ ] Delete Cloud Run after the take
