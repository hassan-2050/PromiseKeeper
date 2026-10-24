# Publishing checklist

- [x] Finish the P0 backend and frontend and verify locally.
- [x] Run real Ollama extraction and preserve model tag/digest and measured evaluation results.
- [x] Capture genuine screenshots and a reproducible silent browser demo; verify video playback.
- [x] Inspect real Kokoro-82M voices and obtain user choice: `af_sarah`.
- [x] Synthesize genuine Kokoro narration, align scenes, create SRT captions and export `final_demo.mp4`.
- [x] Verify the final audio, captions and video: 1920×1080, 112.36 seconds, full FFmpeg decode, non-clipping speech and visually reviewed captions. Local ASR independently recovered the narration and reported evaluation numbers.
- [x] User explicitly approved `hassan-2050/PromiseKeeper` as public. Verified the authenticated account, reviewed 52 staged files for secrets and generated artifacts, created the repository, and pushed `main`: https://github.com/hassan-2050/PromiseKeeper
- [ ] Upload the redesigned `final_demo.mp4` to YouTube and receive its new actual URL. The previous `iBQeWlr3Vbk` upload shows the earlier UI and is not reused as the refreshed demo embed.
- [x] Update the article for the redesigned interface and verification scope. Mark it pending a matching new YouTube URL.
- [x] Push all 10 refreshed screenshots. Verified HTTP 200, PNG content type and byte equality for every URL pinned to redesign commit `ca7f7f1b4ee8bb53049e8db88cf647e37728fe10`; updated the article and README references.
- [ ] After the new URL is verified, finish the ready-to-paste DEV Markdown and present it for review.
- [ ] User reviews the article. DEV publication remains with the user; no automatic publication is authorized.

- [x] Redesign: production build, four backend tests, real-model production browser journey, and 16 scoped automated accessibility checks passed. See `docs/UI_REDESIGN.md`.
