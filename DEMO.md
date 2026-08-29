# Night Desk — ~4 minute demo script

Record unedited. Show the agent working, then show GCP.

## 0:00–0:35 · Problem

Talk over the empty console (sample queue loaded, shift not run).

> Meridian Wallet dumps a review pile every night. Ten cases here — refunds, loyalty farms, card testing, a traveler in Tokyo. A junior analyst would open every one, pull device and points context, write a note, and decide. Most of that is obvious. The two cases that actually need a human get buried.

Point at the **All cases** list. Do not click Run yet.

## 0:35–0:55 · Value

> Night Desk is the night shift. You give it a goal. It plans, gathers context, writes the case note, and a policy guard — not the model — is the last word. Morning inbox is only the real decisions.

Scroll the goal box. Leave the default text.

## 0:55–2:40 · Live run

1. Click **Run night shift**.
2. Stay on the **Agent trace**. Call out, out loud:
   - `Goal accepted. 10 open cases`
   - a `Plan CASE-2401: claim → case file → …`
   - tool lines (`get_device_graph`, `get_loyalty_history`)
   - `wrote note`
   - `CASE-2401 → AUTO_ESCALATE`
3. When it finishes, read the summary: auto-close 2, auto-escalate 6, human_queue 2.
4. Switch to **Human inbox**. Open `CASE-2405` ($1,840 mixed refund) and `CASE-2410` (household points). Show the pre-written note and “Why human”.
5. Open `CASE-2404` on All cases — eight-year customer in Tokyo, auto-closed. Open `CASE-2409` — ATO + refund, auto-escalated.

If the badge says **Planner (no Gemini key)**, say:

> This recording is the tool planner, same tools the ADK agent calls. With `GOOGLE_API_KEY` the shift boss is Gemini 3.5 Flash on Google ADK.

If the badge says **Gemini gemini-3.5-flash**, say that instead and linger on a Gemini tool-call line.

## 2:40–3:50 · Proof of Google Cloud

Switch to the browser / gcloud window you prepared *before* recording:

1. Cloud Run: service `nightdesk`, region `us-central1`, URL `*.run.app`.
2. Open that URL (or `/api/health`) — JSON shows `store: firestore`, `project: tarka-505801`, `model: gemini-3.5-flash`.
3. Firestore console: collection `nightdesk` → `cases` / `shifts`.
4. Pub/Sub: topic `nightdesk-shifts` with a published message, **or** the shift record’s `pubsub_message_id`.
5. Optional: Cloud Run logs showing `Firestore connected` / `Pub/Sub published`.

One sentence:

> Backend is Cloud Run, state is Firestore, shift ingest is Pub/Sub, reasoning is Gemini 3.5 via ADK. Min instances are zero so this does not sit on the bill.

## 3:50–4:00 · Close

Back to the human inbox.

> Ten cases in. Two decisions for a human. That is the chore.

Stop recording.

## Prep checklist (do this before you hit record)

- [ ] `gcloud run deploy` from the README, then leave the service up for the take
- [ ] Console zoom large enough to read the trace
- [ ] Sample queue reseeded (`Reseed sample cases`)
- [ ] Second tab already on Cloud Run + Firestore
- [ ] After the take: `gcloud run services delete nightdesk --region us-central1`
