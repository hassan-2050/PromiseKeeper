# Demo script

**Synthetic example, not an empirical time-saved measurement.** A researcher is waiting for a promised report. Open the actual import screen and paste `demo/synthetic_research_notes.txt`, including its synthetic-data label and the known 2026-10-21 source timestamp. The notes contain an overdue report, an upcoming figures handoff, a conditional appendix, a fulfilled delivery and an unrelated vague thought. Run real local Qwen extraction, inspect the exact evidence, approve the report, and show the overdue count. Prepare an editable follow-up and finish with the privacy controls. No message is sent.

## Captured artifacts

- `demo/assets/video/demo_silent.mp4`: 94.40-second, 1920×1080 browser recording.
- `demo/assets/video/scene_timing.json`: measured scene boundaries for that recording.
- `demo/assets/video/final_demo.mp4`: 113.12-second, 1920×1080 narrated video using the user's selected `af_sarah` Kokoro voice.
- `demo/assets/audio/kokoro_voiceover.wav`: genuine Kokoro-82M speech, mono 24 kHz PCM.
- `demo/assets/audio/subtitles.srt`: captions timed from Kokoro's predicted token durations.
- `demo/assets/audio/narration_script.md`: narration text and final scene timings.
- `demo/assets/audio/narration_provenance.json`: official model revision, weight/voice hashes, package versions and alignment details.
- `demo/assets/screenshots/`: actual dashboard, input notes, evidence, approved outcome, draft and privacy screens.

## Reproduce

Start Ollama and the app against a fresh local demo database, then run `npm run demo:record`. The web URL defaults to `http://localhost:3001`; override it with `DEMO_WEB_URL` if needed. Chrome and Playwright's FFmpeg helper are required (`npx playwright install ffmpeg`). The recorder uses genuine local extraction and fails if import fails. It does not clear existing user data.

Create a separate Python environment and install `demo/requirements.txt`. With FFmpeg and ffprobe on PATH, run `python demo/narrate_demo.py --voice af_sarah`. The first run downloads the official Kokoro weights and English language resources. Caption and video rendering can be repeated without synthesis using `--render-only`.

Original browser actions retain their recorded timing. The renderer holds a scene's final frame when its narration needs more time; the extra holds are documented in provenance. No processing speed or saved-hours claim is derived from the edited runtime.

See `docs/DEMO_VERIFICATION.md` for verification. GitHub publication is deferred until the end at the user's request. The narrated video is ready for the user's review and YouTube upload.
