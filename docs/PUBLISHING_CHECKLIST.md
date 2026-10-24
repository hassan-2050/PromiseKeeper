# Publishing checklist

- [x] Finish the P0 backend and frontend and verify locally.
- [x] Run real Ollama extraction and preserve model tag/digest and measured evaluation results.
- [x] Capture genuine screenshots and a reproducible silent browser demo; verify video playback.
- [x] Inspect real Kokoro-82M voices and obtain user choice: `af_sarah`.
- [x] Synthesize genuine Kokoro narration, align scenes, create SRT captions and export `final_demo.mp4`.
- [x] Verify the final audio, captions and video: 1920×1080, 113.12 seconds, full FFmpeg decode, non-clipping speech and visually reviewed captions. Local ASR independently recovered the narration and reported evaluation numbers.
- [x] User explicitly approved `hassan-2050/PromiseKeeper` as public. Verified the authenticated account, reviewed 52 staged files for secrets and generated artifacts, created the repository, and pushed `main`: https://github.com/hassan-2050/PromiseKeeper
- [ ] After user supplies a real YouTube URL, verify it and embed the actual video ID.
- [x] Prepare the article draft with implementation details, synthetic evaluation limits and actual screenshots. The draft remains clearly marked pending a real YouTube URL and user review.
- [x] Host all seven actual screenshots in the public repository. Verify HTTP 200 and byte equality for every pinned raw URL; use those stable URLs in the article.
- [ ] Prepare and review the final DEV article, then leave publication to the user.
