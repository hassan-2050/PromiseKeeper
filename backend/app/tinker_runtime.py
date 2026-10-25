"""Opt-in hosted inference from a completed, quality-checked experiment only."""
import asyncio
import importlib.util
import json
import os
from functools import lru_cache
from pathlib import Path

from tinker_lab.evaluation import parse_pipeline_output
from tinker_lab.prepare_data import digest


class PreviewSourceError(ValueError):
    pass


def validate_preview_source(text, folder):
    allowed = {json.loads((folder / "demo.json").read_text(encoding="utf-8"))["text"]}
    for name in ("train", "validation", "test"):
        allowed.update(json.loads(line)["text"] for line in (folder / f"{name}.jsonl").read_text(encoding="utf-8").splitlines())
    if text not in allowed:
        raise PreviewSourceError("This research preview accepts only the completed experiment's frozen synthetic examples.")


def verified_configuration():
    configured = os.getenv("TINKER_VERIFIED_RUN")
    if not configured:
        raise ValueError("TINKER_VERIFIED_RUN must point to a completed experiment directory")
    folder = Path(configured).resolve()
    state = json.loads((folder / "run.json").read_text(encoding="utf-8"))
    plan = json.loads((folder / "plan.json").read_text(encoding="utf-8"))
    comparison = json.loads((folder / "comparison.json").read_text(encoding="utf-8"))
    if state["status"] != "completed" or state.get("selection_scoring_version") != 2:
        raise ValueError("The Tinker run must complete validation, held-out evaluation and finalization")
    path = state["selected_checkpoint"]["sampler_path"]
    if not path.startswith("tinker://") or comparison["run"]["selected_checkpoint"]["sampler_path"] != path:
        raise ValueError("Comparison does not verify the selected sampler checkpoint")
    for split, info in plan["dataset_manifest"]["splits"].items():
        if digest(folder / f"{split}.jsonl") != info["sha256"]:
            raise ValueError("Frozen experiment data changed")
    expected_hash = plan["dataset_manifest"]["splits"]["test"]["sha256"]
    if digest(folder / "test.jsonl") != expected_hash or comparison["test_sha256"] != expected_hash:
        raise ValueError("Held-out corpus provenance changed")
    metrics = comparison["metrics"]["pipeline"]
    regressions = []
    for key in ("f1", "owner_accuracy", "date_accuracy"):
        a, b = metrics["baseline"][key], metrics["finetuned"][key]
        if a is None or b is None or b < a:
            regressions.append(key)
    preview = os.getenv("TINKER_SYNTHETIC_PREVIEW", "false").casefold() == "true"
    if regressions and not preview:
        raise ValueError(f"Selected checkpoint regresses on held-out {', '.join(regressions)}; keep the local extractor")
    results = folder / f"{state.get('final_output_prefix', 'finetuned')}-test.jsonl"
    rows = [json.loads(line) for line in results.read_text(encoding="utf-8").splitlines()]
    expected_ids = {json.loads(line)["id"] for line in (folder / "test.jsonl").read_text(encoding="utf-8").splitlines()}
    if len(rows) != len(expected_ids) or {row["id"] for row in rows} != expected_ids:
        raise ValueError("Incomplete held-out output")
    if any(not parse_pipeline_output(row["raw"])[1] or row["stop_reason"] != "stop" for row in rows):
        raise ValueError("Checkpoint returned malformed or truncated held-out output")
    if importlib.util.find_spec("tinker") is None:
        raise ValueError("Install the optional Tinker experiment dependencies")
    from tinker.auth import tinker_has_credentials
    if not tinker_has_credentials():
        raise ValueError("Tinker credentials are not configured for this API process")
    state = {**state, "preview_only": preview, "quality_regressions": regressions}
    return folder, state, plan


@lru_cache(maxsize=2)
def _runtime(folder_name, sampler_path, config_json):
    import tinker
    from transformers import AutoTokenizer
    from tinker_lab.transport import configure_transport
    config = json.loads(config_json)
    configure_transport(config)
    tokenizer = AutoTokenizer.from_pretrained(config["base_model"], revision=config["tokenizer_revision"])
    service = tinker.ServiceClient(display_name="PromiseKeeper opt-in extractor")
    sampler = service.create_sampling_client(model_path=sampler_path)
    return service, sampler, tokenizer, config


async def extract_tinker(text, source_timestamp):
    from tinker_lab.adapter import extract_experimental
    folder, state, plan = verified_configuration()
    if state["preview_only"]:
        validate_preview_source(text, folder)
    runtime = await asyncio.to_thread(_runtime, str(folder), state["selected_checkpoint"]["sampler_path"], json.dumps(plan["config"], sort_keys=True))
    _, sampler, tokenizer, config = runtime
    case = {"id": "opt-in-import", "text": text,
            "source_timestamp": source_timestamp.isoformat() if source_timestamp else None}
    return await extract_experimental(sampler, tokenizer, case, config)
