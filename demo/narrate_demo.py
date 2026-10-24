"""Synthesize the user-selected Kokoro voice and align it with real browser footage.

Run from the repo root: python demo/narrate_demo.py --voice af_sarah
FFmpeg/ffprobe must be on PATH. First run downloads the genuine official weights.
Original action timing is retained; extra narration time holds the scene's last frame.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.metadata
import json
import math
from pathlib import Path
import subprocess
import textwrap
import wave

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
AUDIO = ROOT / "demo/assets/audio"
VIDEO = ROOT / "demo/assets/video"
CACHE = ROOT / ".tools/narration"
MODEL_DIR = ROOT / ".tools/kokoro-model"
REPO = "hexgrad/Kokoro-82M"
REVISION = "f3ff3571791e39611d31c381e3a41a3af07b4987"
SR = 24000
FPS = 25


def run(*args: str):
    subprocess.run(args, cwd=ROOT, check=True)


def wav_write(path: Path, data: np.ndarray):
    if not np.isfinite(data).all():
        raise ValueError("Non-finite audio samples")
    with wave.open(str(path), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes((np.clip(data, -1, 1) * 32767).astype("<i2").tobytes())


def stamp(seconds: float) -> str:
    total = round(seconds * 1000)
    return f"{total//3600000:02}:{total//60000%60:02}:{total//1000%60:02},{total%1000:03}"


def cue_groups(tokens: list[dict], chunk_text: str, duration: float) -> list[dict]:
    """Caption groups use the model's predicted token durations, not word counts."""
    groups = []
    text = ""
    start = None
    end = 0.0
    for token in tokens:
        a, b = token["start"], token["end"]
        piece = token["text"] + token["whitespace"]
        if a is not None and text.strip() and (len(text + piece) > 76 or b-end > 4 or a-(start or 0) > 4.5):
            groups.append({"start": start or 0, "end": min(end + .08, duration), "text": text.strip()})
            text, start = "", None
        if a is not None and start is None:
            start = max(0, a)
        text += piece
        if b is not None:
            end = min(b, duration)
    if text.strip():
        groups.append({"start": start or 0, "end": min(end+.12, duration), "text": text.strip()})
    if not groups:
        raise ValueError(f"No token timestamps for: {chunk_text}")
    return groups


def synthesize(sections, voice: str):
    import torch
    from huggingface_hub import hf_hub_download
    from kokoro import KModel, KPipeline

    torch.set_num_threads(6)
    files = {name: hf_hub_download(REPO, name, revision=REVISION, local_dir=MODEL_DIR)
             for name in ["config.json", "kokoro-v1_0.pth", f"voices/{voice}.pt"]}
    print(f"Loading genuine {REPO}@{REVISION}, voice={voice}", flush=True)
    model = KModel(repo_id=REPO, config=files["config.json"], model=files["kokoro-v1_0.pth"]).eval()
    pipeline = KPipeline(lang_code=voice[0], repo_id=REPO, model=model)
    pack = pipeline.load_voice(files[f"voices/{voice}.pt"])
    for section in sections:
        key = hashlib.sha256((section["text"] + voice + REVISION + "speed=1").encode()).hexdigest()[:12]
        cache = CACHE / f"{section['name']}-{key}.npz"
        meta = cache.with_suffix(".json")
        if cache.exists() and meta.exists():
            print(f"Cached narration: {section['name']}", flush=True)
            continue
        chunks = []
        cues = []
        offset = 0.0
        speak_text = section["text"].replace("Qwen", "[Qwen](/kwɛn/)")
        with torch.inference_mode():
            for result in pipeline(speak_text, voice=pack, speed=1.0):
                audio = result.audio.detach().cpu().numpy().astype(np.float32)
                duration = len(audio)/SR
                tokens = [{"text":t.text,"whitespace":t.whitespace,"start":t.start_ts,"end":t.end_ts} for t in result.tokens or []]
                for cue in cue_groups(tokens, result.graphemes, duration):
                    cues.append({**cue, "start":offset+cue["start"], "end":offset+cue["end"]})
                chunks.append(audio)
                chunks.append(np.zeros(round(.18*SR), dtype=np.float32))
                offset += duration+.18
        if not chunks:
            raise ValueError(f"Kokoro returned no speech for {section['name']}")
        audio = np.concatenate(chunks[:-1])
        np.savez_compressed(cache, audio=audio)
        meta.write_text(json.dumps({"cues":cues,"duration":len(audio)/SR},indent=2),encoding="utf8")
        print(f"Synthesized {section['name']}: {len(audio)/SR:.2f}s", flush=True)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--voice", required=True, help="User-selected official Kokoro voice")
    parser.add_argument("--render-only", action="store_true")
    args = parser.parse_args()
    if args.voice != "af_sarah":
        raise SystemExit("This project's approved voice is af_sarah. Obtain a new user choice before changing it.")
    for p in [AUDIO, VIDEO, CACHE]: p.mkdir(parents=True, exist_ok=True)
    sections = json.loads((ROOT/"demo/narration_sections.json").read_text(encoding="utf8"))
    timing = json.loads((VIDEO/"scene_timing.json").read_text(encoding="utf8"))
    scenes = {x["name"]:x for x in timing["scenes"]}
    if not args.render_only:
        synthesize(sections, args.voice)
    timeline, audio_pieces, cues, clips = [], [], [], []
    offset = 0.0
    for index, section in enumerate(sections):
        key = hashlib.sha256((section["text"]+args.voice+REVISION+"speed=1").encode()).hexdigest()[:12]
        cache = CACHE/f"{section['name']}-{key}.npz"
        speech = np.load(cache)["audio"]
        meta = json.loads(cache.with_suffix(".json").read_text(encoding="utf8"))
        scene = scenes[section["name"]]
        source_duration = scene["end"]-scene["start"]
        duration = math.ceil(max(source_duration, len(speech)/SR+.8)*FPS)/FPS
        lead = .3
        padded = np.zeros(round(duration*SR),dtype=np.float32)
        padded[round(lead*SR):round(lead*SR)+len(speech)] = speech
        audio_pieces.append(padded)
        for cue in meta["cues"]:
            cues.append({**cue,"start":offset+lead+cue["start"],"end":offset+lead+cue["end"]})
        clip = CACHE/f"scene-{index:02}.mp4"
        run("ffmpeg","-y","-v","error","-ss",str(scene["start"]),"-t",str(source_duration),"-i",str(VIDEO/"demo_silent.mp4"),
            "-an","-vf",f"setpts=PTS-STARTPTS,tpad=stop_mode=clone:stop_duration={max(0,duration-source_duration)+.08},fps={FPS}",
            "-t",str(duration),"-c:v","libx264","-preset","fast","-crf","18","-pix_fmt","yuv420p",str(clip))
        clips.append(clip)
        timeline.append({"name":section["name"],"start":round(offset,3),"end":round(offset+duration,3),
                         "source_start":scene["start"],"source_end":scene["end"],"text":section["text"]})
        offset += duration
    if not 90 <= offset <= 150:
        raise ValueError(f"Narrated runtime {offset}s is outside the 90–150s target")
    raw_audio = np.concatenate(audio_pieces)
    peak = float(np.max(np.abs(raw_audio)))
    if peak > .97: raw_audio *= .97/peak
    raw = CACHE/"voiceover_raw.wav"
    wav_write(raw, raw_audio)
    run("ffmpeg","-y","-v","error","-i",str(raw),"-af","loudnorm=I=-16:TP=-1.5:LRA=11","-ar",str(SR),"-c:a","pcm_s16le",str(AUDIO/"kokoro_voiceover.wav"))
    srt = []
    for i, cue in enumerate(cues):
        if cue["end"] <= cue["start"]: raise ValueError("Invalid subtitle cue")
        if i and cue["start"] < cues[i-1]["end"]:
            cues[i-1]["end"] = cue["start"]-.001
    for i, cue in enumerate(cues, 1):
        srt.append(f"{i}\n{stamp(cue['start'])} --> {stamp(cue['end'])}\n{textwrap.fill(cue['text'],width=43)}\n")
    (AUDIO/"subtitles.srt").write_text("\n".join(srt),encoding="utf8")
    manifest = CACHE/"clips.txt"
    manifest.write_text("".join(f"file '{p.as_posix()}'\n" for p in clips),encoding="utf8")
    joined = CACHE/"aligned_silent.mp4"
    run("ffmpeg","-y","-v","error","-f","concat","-safe","0","-i",str(manifest),"-c","copy",str(joined))
    # Captions are burned in for cross-platform readability and included as a selectable track.
    style = "FontName=Arial,FontSize=15,PrimaryColour=&H00FFFFFF,OutlineColour=&H40141414,BorderStyle=3,Outline=1.5,Shadow=0,MarginV=16"
    run("ffmpeg","-y","-v","error","-i",str(joined),"-i",str(AUDIO/"kokoro_voiceover.wav"),"-i",str(AUDIO/"subtitles.srt"),
        "-map","0:v:0","-map","1:a:0","-map","2:0","-vf",f"subtitles=demo/assets/audio/subtitles.srt:force_style='{style}'",
        "-c:v","libx264","-crf","18","-preset","fast","-pix_fmt","yuv420p","-c:a","aac","-b:a","192k","-c:s","mov_text",
        "-metadata:s:s:0","language=eng","-metadata","title=PromiseKeeper | Local AI, human review","-t",str(offset),"-movflags","+faststart",str(VIDEO/"final_demo.mp4"))
    provenance = {"model":REPO,"revision":REVISION,"voice":args.voice,"user_selected":True,
                  "sample_rate":SR,"speech_speed":1.0,"duration":round(offset,3),"caption_timing":"Kokoro predicted token durations",
                  "video_alignment":"Original actions retain their timing; extra narration holds the last frame of a scene.",
                  "packages":{p:importlib.metadata.version(p) for p in ["kokoro","torch","transformers","misaki","spacy"]},
                  "sha256":{f:hashlib.sha256((MODEL_DIR/f).read_bytes()).hexdigest() for f in ["kokoro-v1_0.pth",f"voices/{args.voice}.pt"]},
                  "scenes":timeline}
    (AUDIO/"narration_provenance.json").write_text(json.dumps(provenance,indent=2)+"\n",encoding="utf8")
    script = f"# PromiseKeeper demo narration\n\nVoice: `{args.voice}` (selected by the user). Genuine `{REPO}` with Kokoro 0.9.4.\n\nRuntime: {offset:.2f} seconds. The notes and evaluation set are synthetic. Scene holds allow natural speech without speeding through the original browser actions. Captions use Kokoro's predicted token timing.\n"
    for scene in timeline:
        script += f"\n## {stamp(scene['start'])} – {stamp(scene['end'])} · {scene['name']}\n\n{scene['text']}\n"
    (AUDIO/"narration_script.md").write_text(script,encoding="utf8")
    print(f"Finished: {VIDEO/'final_demo.mp4'} ({offset:.2f}s)",flush=True)


if __name__ == "__main__": main()
