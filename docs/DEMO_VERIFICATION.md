# Narrated demo verification

The user selected `af_sarah` and deferred GitHub publication until the end. Narration uses genuine `hexgrad/Kokoro-82M`, revision `f3ff3571791e39611d31c381e3a41a3af07b4987`, through Kokoro 0.9.4. No replacement speech service was used.

## Media checks

- Final artifact: `demo/assets/video/final_demo.mp4`.
- Runtime: 113.12 seconds; H.264 video at 1920×1080 and 25 fps.
- Audio: AAC in the MP4; source WAV is mono PCM, 24 kHz, 113.12 seconds.
- Video and audio durations match. The final file fully decoded through FFmpeg without reported errors.
- The MP4 includes burned captions and a selectable English `mov_text` subtitle track. Captions come from the saved SRT, using Kokoro's predicted token timings. Caption samples were visually reviewed at full resolution.
- WAV mean level measured -17.7 dBFS and peak level -1.4 dBFS; the output is non-silent and does not clip.
- Local `Systran/faster-whisper-base.en` transcription recovered the narration and all spoken evaluation figures: 55 examples, 40 true positives, no false positives or misses, owner 30/35 and explicit dates 5/5. ASR rendered Qwen/Ollama phonetically and one occurrence of PromiseKeeper differently. This is an automated intelligibility cross-check, not a claim of perfect pronunciation or manual listening.
- Input, evidence, approval, overdue dashboard and follow-up screenshots were captured from the real application. The input data is synthetic. The source recording used real local Qwen inference.

## Timing

The silent recording lasts 94.40 seconds. `demo/assets/video/scene_timing.json` records the actual browser scene boundaries. The narration renderer preserves the original action timing and appends a held final frame when a narration section lasts longer than its scene. Final scene timings and model/voice hashes are saved in `demo/assets/audio/narration_provenance.json`.

The edited duration is not a processing benchmark or a time-saved measurement. Case-level synthetic classification is separate from claim entailment and real-world extraction accuracy; see `docs/EVALUATION.md`.

## Verify again

```powershell
ffprobe -v error -show_entries stream=codec_name,codec_type,width,height,sample_rate,duration:format=duration,size -of json demo/assets/video/final_demo.mp4
ffmpeg -v error -i demo/assets/video/final_demo.mp4 -f null -
ffmpeg -hide_banner -i demo/assets/audio/kokoro_voiceover.wav -af volumedetect -f null -
```

External publication is pending. The user must upload the video to YouTube as Public or Unlisted and return the actual URL. GitHub destination selection and publication will happen afterward, per the user's instruction.
