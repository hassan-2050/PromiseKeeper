# PromiseKeeper

PromiseKeeper is a local-first, evidence-led assistant for conversational commitments. Import notes, review suggestions with their exact source quote, approve what is real, and prepare follow-up drafts for a person to edit. It never sends messages.

[Read the published DEV article](https://dev.to/hassan_shah_733ea1eb37c88/i-built-an-ai-that-remembers-the-promises-we-forget-9db).

![Actual PromiseKeeper dashboard after reviewing synthetic notes](https://raw.githubusercontent.com/hassan-2050/PromiseKeeper/ca7f7f1b4ee8bb53049e8db88cf647e37728fe10/demo/assets/screenshots/overdue-dashboard.png)

## Run locally

Requirements: Python 3.12+, Node 22+, Ollama, and enough memory for the selected local model. The configured model is Qwen3 8B (`qwen3:8b`, 8.2B parameters, Q4_K_M, 5.2 GB download, Apache-2.0 model family). Default model inference is local. The optional Tinker research workflow below requires separate cloud setup and explicit consent.

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

[Watch the updated Tinker experiment demo](https://www.youtube.com/watch?v=5HudDBuLpbU). The 140-second recording shows the measured comparison, a fresh checkpoint import, evidence review, approval and cloud privacy disclosures. See [verification and screenshots](docs/TINKER_DEMO.md). Its local export is `demo/assets/tinker/video/final_demo.mp4`.

[Watch the redesigned interface demo on YouTube](https://www.youtube.com/watch?v=rhyfJHkMmrs). The 112.36-second narrated recording is also available locally at `demo/assets/video/final_demo.mp4`.

The captured browser journey uses real local Qwen inference on explicitly synthetic research notes. The user selected Kokoro's `af_sarah` voice. `demo/assets/video/final_demo.mp4` contains the narrated demo, burned captions and a selectable English caption track. `demo/assets/audio/kokoro_voiceover.wav`, `subtitles.srt` and `narration_provenance.json` preserve the audio, caption timing and model hashes.

To record again, use a fresh local demo database, start the services (the recording defaults to web port 3001), install Chrome and Playwright's video helper (`npx playwright install ffmpeg`), and run `npm run demo:record`. Set `DEMO_WEB_URL` to use another web port. The script captures input notes, actual extraction, evidence review, approval, the overdue dashboard, a follow-up draft and privacy controls, then writes `scene_timing.json`.

For narration, create a separate Python environment, install `demo/requirements.txt`, ensure FFmpeg/ffprobe are on PATH, and run `python demo/narrate_demo.py --voice af_sarah`. The script downloads the official Kokoro-82M revision recorded in provenance, uses natural speech at speed 1.0, holds a scene's final frame when extra narration time is needed, and renders the final MP4. The recording and narration scripts are included; media outputs are local artifacts. Source and screenshots are published at [hassan-2050/PromiseKeeper](https://github.com/hassan-2050/PromiseKeeper). The verified user-supplied YouTube URL is embedded in `docs/DEV_SUBMISSION.md` and the published article. See [publication verification](docs/PUBLICATION_VERIFICATION.md) for the live Tinker article, video embed and screenshot checks.

## UI verification

The charcoal/forest/mint redesign uses a left sidebar, vertical forms and direct review actions. It includes working mobile navigation and help, a date-grouped timeline, draft copy/download, and source-specific deletion. Run `npm run test:e2e` for the real local-model browser journey and `npm run test:a11y` for 16 automated light/dark, dialog and mobile-navigation checks. See [docs/UI_REDESIGN.md](docs/UI_REDESIGN.md) for the verification scope.

## Data and privacy

By default, source data is stored in local SQLite and sent only to the configured Ollama service. Deleting a source removes its linked commitments. Optional Tinker mode sends consented source text to the cloud and discloses that local deletion does not delete provider records. The browser does not auto-send messages or publish content. Back up or delete `backend/promisekeeper.db` to manage the local store.

## Optional Tinker research workflow

An actual [Tinker experiment](docs/TINKER_EXPERIMENT.md) trained hosted Qwen3-8B with six epochs of LoRA SFT on 80 authored synthetic cases. Validation selected epoch 1. On 40 held-out cases, pipeline F1 improved **0.8649 to 0.9254**, with false positives falling from 10 to 4. Recall and owner/date accuracy regressed, and observed latency increased. These are small synthetic-set results, not real-world accuracy claims.

**Ollama remains the default.** The checkpoint fails the production quality guard. A separate research preview accepts only exact frozen synthetic texts and requires cloud consent for every import. The existing quote checks, approval boundary, SQLite, drafts and original demo remain intact. No Gemma or app rebuild is involved.

Review the [full comparison](docs/TINKER_COMPARISON.md), [standalone HTML report](docs/tinker/run-20261025/comparison.html), [raw run bundle](docs/tinker/run-20261025/README.md), [new demo and screenshots](docs/TINKER_DEMO.md) and [DEV article source](docs/DEV_TINKER_ADDENDUM_DRAFT.md). Provider session usage reports approximately $0.063 gross estimated training/sampling cost; invoice cost and credit balance remain unverified. Storage and separate UI preview calls are excluded. Install optional experiment dependencies with `uv pip install --python .venv/Scripts/python.exe -r backend/tinker_lab/requirements.txt` and follow the protocol. The [new video is on YouTube](https://www.youtube.com/watch?v=5HudDBuLpbU); the [DEV article is published](https://dev.to/hassan_shah_733ea1eb37c88/i-built-an-ai-that-remembers-the-promises-we-forget-9db).

## License

MIT for this project code. The selected model has its own Apache-2.0 license and is not bundled.
