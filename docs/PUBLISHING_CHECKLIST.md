# Publishing checklist

- [x] Finish the P0 backend and frontend and verify locally.
- [x] Run real Ollama extraction and preserve model tag/digest and measured evaluation results.
- [x] Capture genuine screenshots and a reproducible silent browser demo; verify video playback.
- [x] Inspect real Kokoro-82M voices and obtain user choice: `af_sarah`.
- [x] Synthesize genuine Kokoro narration, align scenes, create SRT captions and export `final_demo.mp4`.
- [x] Verify the final audio, captions and video: 1920×1080, 112.36 seconds, full FFmpeg decode, non-clipping speech and visually reviewed captions. Local ASR independently recovered the narration and reported evaluation numbers.
- [x] User explicitly approved `hassan-2050/PromiseKeeper` as public. Verified the authenticated account, reviewed 52 staged files for secrets and generated artifacts, created the repository, and pushed `main`: https://github.com/hassan-2050/PromiseKeeper
- [x] Receive the user's redesigned demo URL: https://www.youtube.com/watch?v=rhyfJHkMmrs. YouTube oEmbed returned HTTP 200, title `promise keeper`, and an embed containing the supplied video ID.
- [x] Update the article for the redesigned interface and verification scope, including the verified YouTube embed.
- [x] Push all 10 refreshed screenshots. Verified HTTP 200, PNG content type and byte equality for every URL pinned to redesign commit `ca7f7f1b4ee8bb53049e8db88cf647e37728fe10`; updated the article and README references.
- [x] Finish the ready-to-paste DEV Markdown with the verified new URL and present its complete content in chat for review.
- [x] User published the article and supplied its actual URL: https://dev.to/hassan_shah_733ea1eb37c88/i-built-an-ai-that-remembers-the-promises-we-forget-9db. Verified through the public DEV API, including the rendered YouTube embed and repository link. The agent did not publish it.
- [ ] Restore the five screenshot Markdown lines in the published DEV article. The live article currently contains their captions as plain text and no image elements; all five original screenshot URLs still return HTTP 200 with PNG content. See `docs/PUBLICATION_VERIFICATION.md`.

- [x] Redesign: production build, four backend tests, real-model production browser journey, and 16 scoped automated accessibility checks passed. See `docs/UI_REDESIGN.md`.
