# Devpost submission copy

Paste into the All Things Agentic form. Repo must be public (or shared with testing@devpost.com and cloudhackathons@google.com).

## Project name

Night Desk

## Tagline

The night shift for refund, loyalty, and payment-abuse queues.

## Track

The Taskmaster

## Text description

Night Desk is an autonomous overnight case-triage agent for fraud ops. A consumer wallet (sample tenant: Meridian) dumps a `REVIEW` pile every night — serial refunds, welcome-bonus farms, card testing, friendly-fraud INR claims, the occasional long-tenured traveler. A junior analyst would open every case, pull device and loyalty context, write a note, and decide. Most of that work is obvious. The cases that actually need a human get buried.

You give Night Desk a goal. It is not a chatbot. It plans a work order per open case, calls investigation tools (case file, account, device graph, velocity, loyalty, delivery/travel/ATO), writes a structured case note, and a deterministic policy guard — not the LLM — issues `AUTO_CLOSE`, `AUTO_ESCALATE`, or `HUMAN_QUEUE`. The morning inbox is only the real decisions.

Built for the same domain as Tarka (local-first fraud OS): evaluate fires, Night Desk drains the review pile.

## Features and functionality

- Goal-driven night shift (`POST /api/shifts`) that drains the queue without turn-by-turn prompting
- Google ADK investigator with Gemini 3.5 Flash (tool planner fallback when no API key)
- Tools for case, account, device graph, velocity, loyalty, delivery/travel/ATO
- Structured case notes (summary, evidence, confidence, why-human)
- Deterministic policy guard with a confidence floor
- Human inbox + analyst resolve (close / escalate)
- Live SSE agent trace in the ops console
- Sample 10-case Meridian queue — no secrets required
- Firestore + Pub/Sub on Cloud Run; file-store fallback locally

## Technologies used

- Gemini 3.5 Flash (Gemini API or Vertex AI)
- Google Agent Development Kit (ADK)
- Google Cloud Run, Cloud Firestore, Cloud Pub/Sub
- FastAPI, Next.js, TypeScript, Tailwind CSS
- Python 3.12

## Other data sources used

Synthetic Meridian Wallet cases in `sample_data/cases.json`. No production customer data.

## Findings and learnings

- The valuable agent move in fraud ops is not “chat about a case.” It is “write the note and refuse to auto-act when the policy is thin.”
- A deterministic policy guard behind the model is what makes AUTO_* safe to demo and to test.
- Pub/Sub + Firestore give a real Cloud path without keeping a service warm; Cloud Run min-instances=0 keeps spend near zero.
- A 10-case labeled queue (6 / 2 / 2) is enough to prove the agent acted, not talked.

## Google SDK used

Google ADK (`google-adk`) + Gemini API (`google-genai`). Firestore and Pub/Sub client libraries.

## Date started

29 August 2026

## Pre-existing / third-party code

- Google ADK, google-cloud-firestore, google-cloud-pubsub, FastAPI, Next.js
- No Tarka source was copied; this is a new repo. Domain knowledge only.
