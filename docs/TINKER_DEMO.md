# Tinker demo and verification

The new [140-second narrated demo is on YouTube](https://www.youtube.com/watch?v=5HudDBuLpbU), with its local export at `demo/assets/tinker/video/final_demo.mp4`. It uses the user-selected Kokoro `af_sarah` voice at natural speed, real Tinker outputs and a fresh checkpoint import. The original published demo and its URL remain unchanged.

The user supplied this upload on October 25, 2026. YouTube's oEmbed endpoint returned the title **Tinker-promise** and author **Hassan Shah**. The media checks below describe the verified local export.

## Captured evidence

| Scene | Evidence |
| --- | --- |
| Measured comparison | [Actual pipeline table](../demo/assets/tinker/screenshots/measured-comparison.png), including owner/date and latency regressions |
| Baseline and checkpoint | [Baseline soft refusal error](../demo/assets/tinker/screenshots/baseline-soft-refusal.png) and [fine-tuned empty output](../demo/assets/tinker/screenshots/finetuned-soft-refusal.png) from preserved actual test responses |
| Cloud import | [Frozen messy synthetic input and consent](../demo/assets/tinker/screenshots/cloud-import-consent.png) |
| Fresh inference | [Checkpoint suggestions with literal quotes](../demo/assets/tinker/screenshots/checkpoint-evidence-review.png) |
| Human review | [Simulated reviewer clarifies the condition](../demo/assets/tinker/screenshots/reviewer-clarifies-action.png) before approval |
| Follow-up | [Approved commitment and editable draft](../demo/assets/tinker/screenshots/approved-followup-draft.png); nothing sent |
| Privacy | [Cloud processing and local deletion boundary](../demo/assets/tinker/screenshots/cloud-privacy-boundary.png) |

The refusal was selected after evaluation to illustrate fewer false positives, not as another benchmark. The fixed messy transcript has no detection gain: both models missed Cleo's migration-guide commitment. The narration says so. All notes and reviewer edits are synthetic. Baseline-versus-tuned report panels show preserved actual API responses; the subsequent UI extraction makes a fresh remote request, without mocked/replayed suggestions.

The production quality guard rejects the checkpoint's owner/date regressions. The isolated demonstration explicitly sets `TINKER_SYNTHETIC_PREVIEW=true`, accepts only exact frozen synthetic texts and requires per-import cloud consent. The recorder checks the live sampler path, consent initially unchecked, submit initially disabled, actual HTTP success, literal evidence, review/approval/drafting and absence of browser errors. It uses a separate SQLite database under ignored `.tools/`.

The SDK/sampler is warmed with a separate frozen negative training example before capture, and that source is deleted. Video scene holds support natural narration; 0.6 seconds are trimmed from scene ends to avoid holding frames from the next scene. This edited recording is not a latency or time-saved measurement. Benchmark latency retains its original cold calls.

## Media verification

The final MP4 has 1920 x 1080 H.264 video at 25 fps, 24 kHz AAC audio and a selectable English `mov_text` caption track, plus burned captions. Video/audio durations both equal 140.00 seconds; captions end at 139.48 seconds. Full FFmpeg decode completed without errors. Source WAV mean level is -17.2 dBFS with peak -1.5 dBFS; it is non-silent and does not clip. Representative rendered comparison, consent and review frames were visually checked.

A local `Systran/faster-whisper-base.en` transcription recovered the spoken F1 values (0.865 and 0.925), the regressions, cloud consent, missed guide commitment and approval boundary. It rendered Qwen/Ollama phonetically. This is an automated intelligibility cross-check, not a claim of manual listening or perfect pronunciation.

Capture provenance, checkpoint identity, synthetic source ID and original scene timings are in [capture_provenance.json](../demo/assets/tinker/capture_provenance.json). Voice/model hashes, packages and edited scene timings are in [narration_provenance.json](../demo/assets/tinker/audio/narration_provenance.json); the [script](../demo/assets/tinker/audio/narration_script.md) and [SRT](../demo/assets/tinker/audio/subtitles.srt) preserve narration and captions. Large MP4/WAV/WebM files are ignored local artifacts; screenshots, scripts and provenance are available for review.

The original `demo/assets/video/final_demo.mp4` still has SHA-256 `95a24c3217b73eb9742078f67ba2f64fa82162c3251fde34ec99d01a4ecad2ed`.

## Reproduce

Start a separate API against a fresh synthetic demo database using optional Tinker dependencies, the locally configured key, `EXTRACTION_PROVIDER=tinker`, `TINKER_SYNTHETIC_PREVIEW=true` and an absolute `TINKER_VERIFIED_RUN` pointing at the completed run. Start the production web build on port 3001 with its API at port 9000. Retain the normal local app database. Remote checkpoints may expire after their seven-day TTL.

```powershell
node demo/record_tinker_demo.mjs --run-dir backend/tinker_lab/runs/qwen3-8b-20261025-01
.tools/kokoro/Scripts/python.exe demo/narrate_demo.py --voice af_sarah --sections demo/tinker_narration_sections.json --assets-dir demo/assets/tinker --cache-dir .tools/tinker-narration --min-duration 90 --max-duration 300 --scene-end-trim 0.6 --title "PromiseKeeper | Tinker experiment and human review"
ffprobe -v error -show_entries stream=codec_name,codec_type,duration:format=duration,size -of json demo/assets/tinker/video/final_demo.mp4
ffmpeg -v error -i demo/assets/tinker/video/final_demo.mp4 -f null -
```

Twenty backend tests pass, including extraction/evidence/approval regressions, consent boundaries, synthetic allowlisting, scorer parity and a stubbed offline training-workflow test. That test's dummy outputs stay in temporary directories and are not experiment evidence. The frontend production build and TypeScript checks passed. The real local Ollama browser smoke journey passed. Automated axe checks found zero violations in 16 tested light/dark, dialog and mobile navigation states in both local mode and the cloud preview; see [preview report](tinker/ui_accessibility-preview.json). This is scoped automated checking, not a complete accessibility audit.
