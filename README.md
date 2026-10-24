# PromiseKeeper

PromiseKeeper is a local-first, evidence-led assistant for conversational commitments. Import notes, review suggestions with their exact source quote, approve what is real, and prepare follow-up drafts for a person to edit. It never sends messages.

[Read the published DEV article](https://dev.to/hassan_shah_733ea1eb37c88/i-built-an-ai-that-remembers-the-promises-we-forget-9db).

![Actual PromiseKeeper dashboard after reviewing synthetic notes](https://raw.githubusercontent.com/hassan-2050/PromiseKeeper/ca7f7f1b4ee8bb53049e8db88cf647e37728fe10/demo/assets/screenshots/overdue-dashboard.png)

## Run locally

Requirements: Python 3.12+, Node 22+, Ollama, and enough memory for the selected local model. The configured model is Qwen3 8B (`qwen3:8b`, 8.2B parameters, Q4_K_M, 5.2 GB download, Apache-2.0 model family). Model inference is local; do not configure a cloud endpoint.

1. Install and start Ollama, then fetch the model: `ollama pull qwen3:8b`.
2. In one terminal: `cd backend; python -m venv .venv; .venv\Scripts\Activate.ps1; pip install -r requirements.txt; uvicorn app.main:app --reload --port 9000`.
3. In another terminal at the project root: `npm install; npm run dev`.
4. Open `http://localhost:3000`. API health is available at `http://localhost:9000/api/health`.

macOS/Linux activation: `source .venv/bin/activate`. The API defaults to a SQLite database in `backend/promisekeeper.db`; set `DATABASE_URL`, `OLLAMA_URL`, `OLLAMA_MODEL` in your environment as needed. Copy `.env.example` as a reference; secrets are not needed.

Docker Compose is provided for the API and web app and expects Ollama to run on the host. Run `docker compose up --build` after pulling the model on the host.

## How it works

The API sends source text to Ollama with a constrained JSON extraction prompt. Pydantic validates request and response boundaries; the backend independently rejects any proposed evidence quote that is not an exact substring of the imported text. Suggestions remain suggested until a person approves them. Unknown deadlines and owners remain unresolved. Follow-up drafts use only approved commitment fields and require human review.

## Current scope

The app supports pasted text and `.txt`/`.md` import, paragraph fragments with source offsets, exact duplicate grouping with multiple evidence quotes, approval/edit/reject/complete actions, private notes, audit events, dashboard summaries, a timeline, local source deletion, editable follow-up drafts, and confirmed-item CSV export. A measured 55-case synthetic evaluation is documented in [docs/EVALUATION.md](docs/EVALUATION.md). It does not yet provide semantic deduplication or PDF/audio ingestion. Synthetic-set results do not establish real-world accuracy; model suggestions need review.

## Demo and narration

[Watch the redesigned interface demo on YouTube](https://www.youtube.com/watch?v=rhyfJHkMmrs). The 112.36-second narrated recording is also available locally at `demo/assets/video/final_demo.mp4`.

The captured browser journey uses real local Qwen inference on explicitly synthetic research notes. The user selected Kokoro's `af_sarah` voice. `demo/assets/video/final_demo.mp4` contains the narrated demo, burned captions and a selectable English caption track. `demo/assets/audio/kokoro_voiceover.wav`, `subtitles.srt` and `narration_provenance.json` preserve the audio, caption timing and model hashes.

To record again, use a fresh local demo database, start the services (the recording defaults to web port 3001), install Chrome and Playwright's video helper (`npx playwright install ffmpeg`), and run `npm run demo:record`. Set `DEMO_WEB_URL` to use another web port. The script captures input notes, actual extraction, evidence review, approval, the overdue dashboard, a follow-up draft and privacy controls, then writes `scene_timing.json`.

For narration, create a separate Python environment, install `demo/requirements.txt`, ensure FFmpeg/ffprobe are on PATH, and run `python demo/narrate_demo.py --voice af_sarah`. The script downloads the official Kokoro-82M revision recorded in provenance, uses natural speech at speed 1.0, holds a scene's final frame when extra narration time is needed, and renders the final MP4. The recording and narration scripts are included; media outputs are local artifacts. Source and screenshots are published at [hassan-2050/PromiseKeeper](https://github.com/hassan-2050/PromiseKeeper). The verified user-supplied YouTube URL is embedded in `docs/DEV_SUBMISSION.md` and the published article. See [publication verification](docs/PUBLICATION_VERIFICATION.md) for the remaining screenshot formatting fix on DEV.

## UI verification

The charcoal/forest/mint redesign uses a left sidebar, vertical forms and direct review actions. It includes working mobile navigation and help, a date-grouped timeline, draft copy/download, and source-specific deletion. Run `npm run test:e2e` for the real local-model browser journey and `npm run test:a11y` for 16 automated light/dark, dialog and mobile-navigation checks. See [docs/UI_REDESIGN.md](docs/UI_REDESIGN.md) for the verification scope.

## Data and privacy

All source data is stored in local SQLite and is sent only to the configured Ollama service. Deleting a source removes its linked commitments. The browser does not auto-send or publish any content. Back up or delete `backend/promisekeeper.db` to manage the local store.

## License

MIT for this project code. The selected model has its own Apache-2.0 license and is not bundled.
