# Narrated demo verification

The original local-model demo verified below is preserved. The separate, completed Tinker experiment has its own [new demo and verification](TINKER_DEMO.md), with mixed results and cloud processing disclosed.

The user selected `af_sarah` and approved the public repository `hassan-2050/PromiseKeeper`. Narration uses genuine `hexgrad/Kokoro-82M`, revision `f3ff3571791e39611d31c381e3a41a3af07b4987`, through Kokoro 0.9.4. No replacement speech service was used.

## Media checks

- Final artifact: `demo/assets/video/final_demo.mp4`.
- Runtime: 112.36 seconds; H.264 video at 1920×1080 and 25 fps.
- Audio: AAC in the MP4; source WAV is mono PCM, 24 kHz, 112.36 seconds.
- Video and audio durations match. The final file fully decoded through FFmpeg without reported errors.
- The MP4 includes burned captions and a selectable English `mov_text` subtitle track. Captions come from the saved SRT, using Kokoro's predicted token timings. Caption samples were visually reviewed at full resolution.
- WAV mean level measured -17.6 dBFS and peak level -1.4 dBFS; the output is non-silent and does not clip.
- Local `Systran/faster-whisper-base.en` transcription recovered the narration and all spoken evaluation figures: 55 examples, 40 true positives, no false positives or misses, owner 30/35 and explicit dates 5/5. ASR rendered Qwen/Ollama phonetically and one occurrence of PromiseKeeper differently. This is an automated intelligibility cross-check, not a claim of perfect pronunciation or manual listening.
- Input, evidence, approval, overdue dashboard and follow-up screenshots were captured from the real application. The input data is synthetic. The source recording used real local Qwen inference.

The redesign reuses the previously synthesized, user-approved genuine Sarah speech segments at natural speed. They were freshly aligned and padded against the new production recording, then normalized and captioned again. The final video fully decoded through FFmpeg; the saved captions match all narration text.

## Timing

The silent recording lasts 91.00 seconds. `demo/assets/video/scene_timing.json` records the actual browser scene boundaries. The narration renderer preserves the original action timing and appends a held final frame when a narration section lasts longer than its scene. Final scene timings and model/voice hashes are saved in `demo/assets/audio/narration_provenance.json`.

The edited duration is not a processing benchmark or a time-saved measurement. Case-level synthetic classification is separate from claim entailment and real-world extraction accuracy; see `docs/EVALUATION.md`.

## Verify again

```powershell
ffprobe -v error -show_entries stream=codec_name,codec_type,width,height,sample_rate,duration:format=duration,size -of json demo/assets/video/final_demo.mp4
ffmpeg -v error -i demo/assets/video/final_demo.mp4 -f null -
ffmpeg -hide_banner -i demo/assets/audio/kokoro_voiceover.wav -af volumedetect -f null -
```

Source and actual screenshots are published at [hassan-2050/PromiseKeeper](https://github.com/hassan-2050/PromiseKeeper). The user supplied the [refreshed demo on YouTube](https://www.youtube.com/watch?v=rhyfJHkMmrs). YouTube oEmbed returned HTTP 200, title `promise keeper`, and embed HTML containing video ID `rhyfJHkMmrs`. This verifies that the supplied video is available for embedding; it does not establish byte equality with the local export. The user published the [DEV article](https://dev.to/hassan_shah_733ea1eb37c88/i-built-an-ai-that-remembers-the-promises-we-forget-9db); its YouTube embed is present. See `docs/PUBLICATION_VERIFICATION.md` for the pending screenshot formatting fix.
