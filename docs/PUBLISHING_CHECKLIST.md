# Publishing checklist

- [x] Finish the P0 backend and frontend and verify locally.
- [x] Run real Ollama extraction and preserve model tag/digest and measured evaluation results.
- [x] Capture genuine screenshots and a reproducible silent browser demo; verify video playback.
- [x] Inspect real Kokoro-82M voices and obtain user choice: `af_sarah`.
- [x] Synthesize genuine Kokoro narration, align scenes, create SRT captions and export `final_demo.mp4`.
- [x] Verify the final audio, captions and video: 1920×1080, 113.12 seconds, full FFmpeg decode, non-clipping speech and visually reviewed captions. Local ASR independently recovered the narration and reported evaluation numbers.
- [ ] GitHub publication deferred by user until the end. Ask for the destination and visibility then; inspect sensitive files and existing remotes before any remote mutation.
- [ ] After user supplies a real YouTube URL, verify it and embed the actual video ID.
- [x] Prepare the article draft with implementation details, synthetic evaluation limits and actual local screenshots. The 1,912-word draft is clearly marked pending external links and user review.
- [ ] Host the actual screenshots in the selected GitHub repository and replace local draft image references with verified stable URLs.
- [ ] Prepare and review the final DEV article, then leave publication to the user.
