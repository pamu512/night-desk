# Devpost submission copy

Do not file until the owner says so. Repo: https://github.com/pamu512/night-desk

## Project name

Night Desk

## Tagline

The guard that holds. HOLD or ESCALATE — never close money unattended.

## Track

The Taskmaster

## Toll

**Demo runtime is Gemini 3.5 + ADK + GCP; Night Desk is a transferable skill on the buyer’s BYOM/VPC — not a hosted agent seat or a case CRM.**

## Text description

Night Desk stamps hold receipts on an overnight refund / loyalty / payment-abuse review dump. It is not a chatbot and not a shrinking inbox.

A goal starts a shift. Tools pull case, device graph, velocity, loyalty, delivery, ATO. Gemini 3.5 via Google ADK writes the note only. `decide()` then stamps the receipt: `{HOLD|ESCALATE}: {policy reason}`. Evidence is the facts that fired (device_ring, bonuses, fails/BINs, INR+POD, ATO) — not the narrative. If Gemini disagrees, the receipt shows the override.

If Vertex, Gemini, or Pub/Sub is down, every case HOLDs. First-open is that receipt, still on the row, with why + present/missing. There is no AUTO_CLOSE.

## Features and functionality

- Goal-driven shift; Gemini writes notes; `decide()` is last word
- Two-way dispositions: HOLD, ESCALATE
- Fail-closed HOLD when Gemini, Vertex, or Pub/Sub is missing
- Receipt on every row: why, present, missing
- Override visible when the model disagrees
- Sample Meridian cases — no secrets
- Firestore + Pub/Sub on Cloud Run

## Technologies used

- Gemini 3.5 Flash (Gemini API or Vertex AI)
- Google Agent Development Kit (ADK)
- Google Cloud Run, Cloud Firestore, Cloud Pub/Sub
- FastAPI, Next.js, TypeScript, Tailwind CSS
- Python 3.12

## Other data sources used

Synthetic Meridian Wallet cases in `sample_data/cases.json`. No production customer data.

## Findings and learnings

- Closing money unattended is the product failure. HOLD is the feature.
- The demo that matters is the guard holding when Gemini/Vertex is down.
- Gemini never AUTO_CLOSE. The stamp is `decide()`.

## Google SDK used

Google ADK (`google-adk`) + Gemini API (`google-genai`). Firestore and Pub/Sub clients.

## Date started

29 August 2026

## Pre-existing / third-party code

Google ADK, google-cloud-firestore, google-cloud-pubsub, FastAPI, Next.js. New repo.
