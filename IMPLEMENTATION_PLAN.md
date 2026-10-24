# Implementation plan

1. Inspect local runtime availability and verify the non-Gemma local model choice, license, and specs.
2. Build the FastAPI + SQLite backend as a thin end-to-end vertical slice: ingest text, extract evidence-backed commitments via local Ollama, review and approve/edit/reject, draft human-reviewed follow-ups, dashboard and export.
3. Build the responsive Next.js/TypeScript/Tailwind UI for dashboard, import/review, timeline/follow-ups and privacy controls, with visible model and processing status.
4. Add reproducible synthetic demo inputs/gold data, API/backend/frontend coverage, Docker Compose and manual setup docs; run available application and real-model checks.
5. Capture genuine application screenshots/video if browser automation and inference are available, and prepare evaluation, architecture, demo and publishing handoff docs. Stop at each explicitly required external account/voice/YouTube checkpoint.

## UI revision

- Follow the user's design constraints: left sidebar, vertically stacked forms, charcoal/forest/mint palette, direct actions without wizard or stepper controls. Avoid top navigation, horizontal form choices and blue/amber styling.
- Refresh all views with readable evidence cards, a working mobile navigation drawer, source-specific privacy controls, and reliable action/error feedback.
- Verify the revised journeys, capture fresh screenshots and browser footage, realign the approved Sarah narration, update the article and repository, and hand off the revised video for a new YouTube upload.
