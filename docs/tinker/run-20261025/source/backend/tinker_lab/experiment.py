"""Run from backend: python -m tinker_lab.experiment --help.

The run command performs paid remote operations. Other commands never train.
"""
import argparse
import asyncio
import importlib.metadata
import json
import math
import os
import random
import re
import subprocess
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.parse import unquote, urlparse

import httpx

from .adapter import make_datum, prompt_tokens, sample_case
from .evaluation import score
from .prepare_data import DATA, HERE, digest, prepare, write_json
from .transport import configure_transport

ROOT = HERE.parents[1]
PRICING_URL = "https://tinker-docs.thinkingmachines.ai/tinker/models.json"


def now():
    return datetime.now(timezone.utc).isoformat()


def load(path):
    return json.loads(path.read_text(encoding="utf-8"))


def load_cases(split):
    return [json.loads(line) for line in (DATA / f"{split}.jsonl").read_text(encoding="utf-8").splitlines()]


def verify_data():
    manifest = load(DATA / "manifest.json")
    for split, info in manifest["splits"].items():
        if digest(DATA / f"{split}.jsonl") != info["sha256"]:
            raise ValueError(f"{split} differs from the frozen manifest")
        if any(not c.get("synthetic") or c["split"] != split for c in load_cases(split)):
            raise ValueError("Only labeled synthetic data in its declared split may be sent")
    if digest(HERE / "prepare_data.py") != manifest["generator_sha256"]:
        raise ValueError("Generator changed; regenerate and review the dataset before running")
    return manifest


def config_from(path):
    config = load(path)
    if config["base_model"] != "Qwen/Qwen3-8B":
        raise ValueError("This workflow is verified locally only for the Qwen3-8B chat template")
    if not re.fullmatch(r"[a-f0-9]{40}", config.get("tokenizer_revision", "")):
        raise ValueError("Pin tokenizer_revision to an exact Hugging Face commit")
    if config.get("http_transport") != "httpx_http2":
        raise ValueError("Use the reviewed httpx_http2 transport")
    for key in ("rank", "epochs", "batch_size", "max_tokens", "checkpoint_ttl_seconds"):
        if not isinstance(config[key], int) or config[key] <= 0:
            raise ValueError(f"{key} must be a positive integer")
    if not math.isfinite(config["learning_rate"]) or config["learning_rate"] <= 0:
        raise ValueError("learning_rate must be positive and finite")
    if config["temperature"] != 0 or not isinstance(config["seed"], int):
        raise ValueError("Comparison requires temperature zero and a fixed integer seed")
    if not 3600 <= config["checkpoint_ttl_seconds"] <= 315360000:
        raise ValueError("Checkpoint TTL must be between one hour and ten years")
    return config


async def pricing(model):
    async with httpx.AsyncClient(timeout=30, follow_redirects=True) as client:
        response = await client.get(PRICING_URL)
        response.raise_for_status()
    models = response.json()
    if isinstance(models, dict):
        models = models["models"]
    selected = next((m for m in models if m["tinker_id"] == model), None)
    if selected is None:
        raise ValueError("Configured model is absent from the current public price list")
    rates = {name: float(selected[name].replace("$", "").replace(",", "")) for name in ("prefill", "cached_prefill", "sample", "train")}
    return {"retrieved_at": now(), "source": PRICING_URL, "model": selected, "rates_per_million_usd": rates}


async def fetch_capabilities():
    from tinker.auth import get_tinker_token
    from tinker.types import GetServerCapabilitiesResponse
    key = get_tinker_token()
    if not key:
        raise ValueError("This experiment needs an environment or stored API key")
    base = os.getenv("TINKER_BASE_URL", "https://tinker.thinkingmachines.dev/services/tinker-prod").rstrip("/")
    for attempt in range(3):
        try:
            async with httpx.AsyncClient(timeout=20, http2=True) as client:
                response = await client.get(f"{base}/api/v1/get_server_capabilities", headers={"X-API-Key": key})
                response.raise_for_status()
            return GetServerCapabilitiesResponse.model_validate(response.json())
        except (httpx.TimeoutException, httpx.NetworkError):
            if attempt == 2:
                raise
            print(f"Tinker access probe retry {attempt + 1}/2", flush=True)
            await asyncio.sleep(1)


async def preflight(config):
    from tinker.auth import tinker_has_credentials
    result = {"checked_at": now(), "sdk_version": importlib.metadata.version("tinker"),
              "configured_model": config["base_model"], "pricing": await pricing(config["base_model"]),
              "credentials_available": False, "account_models": None, "account_credits_usd": None,
              "credit_status": "Claim free Tinker partner credits at https://hacktoberfest.com/my/promos, then verify the balance in Tinker. No paid funding is assumed.",
              "training_run": "not_started", "status": "access_required"}
    result["credentials_available"] = tinker_has_credentials()
    if not result["credentials_available"]:
        result["action_required"] = "Claim partner credits; run tinker auth login or set TINKER_API_KEY locally; confirm a credit-use limit."
        return result
    try:
        capabilities = await fetch_capabilities()
    except httpx.TimeoutException:
        result["status"] = "connection_timeout"
        result["action_required"] = "Credentials are configured locally, but API access timed out. Check network connectivity; no training has started."
        return result
    except (httpx.HTTPError, ValueError) as exc:
        result["status"] = "access_rejected"
        result["error_type"] = type(exc).__name__
        result["action_required"] = "Check the configured credential, account access and network."
        return result
    result["account_models"] = [m.model_dump(mode="json") for m in capabilities.supported_models]
    supported = next((m for m in capabilities.supported_models if m.model_name == config["base_model"]), None)
    result["status"] = "ready_for_budget_review" if supported and supported.trainable is not False and supported.sampleable is not False else "model_unavailable"
    return result


def demo_case():
    text = ("Synthetic handoff, noisy meeting notes\n"
            "Amina: I sent last month's vendor packet already.\n"
            "Bilal: A new packet could be useful, but I haven't agreed to one.\n"
            "Cleo: Leave the migration guide with me.\n"
            "Dario: If security signs off, I'll review the access matrix by 2026-11-18.\n"
            "Amina: Someone still needs to send the incident digest. Owner undecided.")
    def gold(claim, owner, quote, terms, deadline=None, condition=None):
        return {"claim": claim, "owner": owner, "recipient": None, "deadline": deadline,
                "conditionality": condition, "certainty": "suggested" if owner else "ambiguous",
                "evidence": quote, "action": "Review this commitment", "match_terms": terms.split()}
    return {"id": "demo-messy-handoff", "synthetic": True, "category": "demo", "text": text,
            "source_timestamp": None, "gold": [
                gold("handle the migration guide", "Cleo", "Leave the migration guide with me.", "migration guide"),
                gold("review the access matrix", "Dario", "If security signs off, I'll review the access matrix by 2026-11-18.",
                     "access matrix", "2026-11-18", "security signs off"),
                gold("send the incident digest", None, "Someone still needs to send the incident digest. Owner undecided.", "incident digest")]}


def build_plan(config, tokenizer, price):
    datasets = {split: load_cases(split) for split in ("train", "validation", "test")}
    datums = [make_datum(tokenizer, case) for case in datasets["train"]]
    train_tokens = sum(d.model_input.length for d in datums) * config["epochs"]
    sampling_cases = (datasets["validation"] * (config["epochs"] + 1)
                      + datasets["test"] * 2 + [demo_case()] * 2)
    prefill_tokens = sum(len(prompt_tokens(tokenizer, case)) for case in sampling_cases)
    output_tokens = len(sampling_cases) * config["max_tokens"]
    rates = price["rates_per_million_usd"]
    token_bound = (train_tokens * rates["train"] + prefill_tokens * rates["prefill"] + output_tokens * rates["sample"]) / 1e6
    return {"generated_at": now(), "config": config, "training_tokens": train_tokens,
            "sampling_prompt_tokens": prefill_tokens, "max_sampling_output_tokens": output_tokens,
            "sampling_requests": len(sampling_cases), "training_steps": math.ceil(len(datums) / config["batch_size"]) * config["epochs"],
            "token_cost_upper_estimate_usd": token_bound,
            "buffered_estimate_usd": token_bound * 1.25 + 1.0,
            "cost_caveat": "Rate-card estimate, not a hard provider billing cap. Includes 25% token buffer and $1 storage reserve; storage, retries and rate changes may differ. Set provider billing controls too.",
            "dataset_manifest": verify_data(), "pricing": price,
            "protocol": "Baseline validation + test before training; choose epoch on validation F1, validity, owner accuracy; test chosen checkpoint once; fixed separate demo."}


def append_row(path, value):
    with path.open("a", encoding="utf-8") as file:
        file.write(json.dumps(value, ensure_ascii=False) + "\n")
        file.flush()


async def evaluate(client, tokenizer, cases, config, output):
    rows = []
    for case in cases:
        # Fail the run on a transport error rather than silently compare an
        # incomplete benchmark. Previously completed outputs remain on disk.
        row = await sample_case(client, tokenizer, case, config)
        append_row(output, row)
        rows.append(row)
        print(f"{output.stem}: {len(rows)}/{len(cases)}", flush=True)
    result = {"raw": score(cases, rows, pipeline=False), "pipeline": score(cases, rows)}
    write_json(output.with_suffix(".metrics.json"), result)
    return result


def selection_key(metrics):
    p = metrics["pipeline"]
    return tuple(p[name] if p[name] is not None else -1 for name in ("f1", "output_validity", "owner_accuracy"))


async def billing_snapshot(service, run_dir, started_at, session_id):
    start = datetime.fromisoformat(started_at).replace(minute=0, second=0, microsecond=0)
    end = datetime.now(timezone.utc).replace(minute=0, second=0, microsecond=0) + timedelta(hours=1)
    try:
        response = await service.create_rest_client().get_billing_usage_async(start, end)
        events = [e.model_dump(mode="json") for e in response.data if e.session_id == session_id]
        value = {"captured_at": now(), "session_id": session_id, "events": events,
                 "cost_data_through": response.cost_data_through.isoformat() if response.cost_data_through else None,
                 "actual_invoice_cost_usd": None,
                 "note": "Session-filtered provider usage; estimated gross cost is not the invoice amount. Data may lag hours. Unattributed storage is excluded, not assumed free."}
    except Exception as exc:
        value = {"captured_at": now(), "actual_invoice_cost_usd": None, "events": None,
                 "error_type": type(exc).__name__, "note": "Billing view permission or reconciled data unavailable; costs remain unknown."}
    write_json(run_dir / "billing.json", value)


async def run(config, run_dir, max_estimated_usd):
    import tinker
    from transformers import AutoTokenizer
    if not math.isfinite(max_estimated_usd) or max_estimated_usd <= 0:
        raise ValueError("Set a positive finite maximum estimated USD spend")
    if run_dir.exists():
        raise ValueError("Run directory already exists; outputs are immutable. Do not rerun held-out data to tune a result.")
    verify_data()
    configure_transport(config)
    access = await preflight(config)
    if access["status"] != "ready_for_budget_review":
        raise ValueError("Tinker access/model unavailable; run preflight and complete account setup")
    tokenizer = AutoTokenizer.from_pretrained(config["base_model"], revision=config["tokenizer_revision"])
    plan = build_plan(config, tokenizer, access["pricing"])
    if plan["buffered_estimate_usd"] > max_estimated_usd:
        raise ValueError(f"Buffered estimate ${plan['buffered_estimate_usd']:.4f} exceeds the configured spending estimate limit")
    run_dir.mkdir(parents=True)
    write_json(run_dir / "plan.json", plan)
    write_json(run_dir / "preflight.json", access)
    for split in ("train", "validation", "test"):
        (run_dir / f"{split}.jsonl").write_bytes((DATA / f"{split}.jsonl").read_bytes())
    write_json(run_dir / "demo.json", demo_case())
    # uv-created environments may not include pip; metadata records work in both.
    packages = sorted(f"{d.metadata['Name']}=={d.version}" for d in importlib.metadata.distributions())
    (run_dir / "environment.txt").write_text("\n".join(packages) + "\n", encoding="utf-8")
    revision = subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT, capture_output=True, text=True)
    source_files = [*HERE.glob("*.py"), ROOT / "backend/app/extraction_contract.py"]
    write_json(run_dir / "code.json", {"git_head": revision.stdout.strip(),
               "source_sha256": {str(p.relative_to(ROOT)): digest(p) for p in source_files}})
    for path in source_files:
        target = run_dir / "source" / path.relative_to(ROOT)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(path.read_bytes())
    state = {"status": "running", "started_at": now(), "max_estimated_usd": max_estimated_usd,
             "actual_invoice_cost_usd": None, "selected_checkpoint": None, "checkpoints": []}
    write_json(run_dir / "run.json", state)
    with tinker.ServiceClient(display_name=f"PromiseKeeper {run_dir.name}",
                             user_metadata={"experiment": run_dir.name, "synthetic_only": "true"}) as service:
        try:
            base = await service.create_sampling_client_async(base_model=config["base_model"])
            state["console_url"] = service.get_console_url()
            state["session_id"] = unquote(urlparse(state["console_url"]).path.rstrip("/").split("/")[-1])
            write_json(run_dir / "run.json", state)
            validation, test = load_cases("validation"), load_cases("test")
            await evaluate(base, tokenizer, validation, config, run_dir / "baseline-validation.jsonl")
            await evaluate(base, tokenizer, test, config, run_dir / "baseline-test.jsonl")
            await evaluate(base, tokenizer, [demo_case()], config, run_dir / "baseline-demo.jsonl")
            training = await service.create_lora_training_client_async(
                base_model=config["base_model"], rank=config["rank"], seed=config["seed"],
                user_metadata={"experiment": run_dir.name})
            datums = [make_datum(tokenizer, case) for case in load_cases("train")]
            best_key = None
            for epoch in range(config["epochs"]):
                indices = list(range(len(datums)))
                random.Random(config["seed"] + epoch).shuffle(indices)
                for step, offset in enumerate(range(0, len(indices), config["batch_size"])):
                    batch = [datums[i] for i in indices[offset:offset + config["batch_size"]]]
                    started = time.perf_counter()
                    future = await training.forward_backward_async(batch, "cross_entropy")
                    optim = await training.optim_step_async(tinker.AdamParams(learning_rate=config["learning_rate"]))
                    output = await future.result_async()
                    await optim.result_async()
                    logprobs = [v for item in output.loss_fn_outputs for v in item["logprobs"].tolist()]
                    weights = [v for datum in batch for v in datum.loss_fn_inputs["weights"].tolist()]
                    if len(logprobs) != len(weights) or not sum(weights):
                        raise ValueError("Unexpected SDK loss output shape")
                    append_row(run_dir / "training.jsonl", {"epoch": epoch + 1, "step": step + 1, "at": now(),
                        "loss": -sum(p * w for p, w in zip(logprobs, weights)) / sum(weights),
                        "tokens": sum(d.model_input.length for d in batch), "metrics": output.metrics,
                        "seconds": time.perf_counter() - started})
                    print(f"Training epoch {epoch + 1}, batch {step + 1}", flush=True)
                save = await training.save_state_async(name=f"epoch-{epoch+1}", ttl_seconds=config["checkpoint_ttl_seconds"])
                resume_path = (await save.result_async()).path
                save = await training.save_weights_for_sampler_async(name=f"epoch-{epoch+1}", ttl_seconds=config["checkpoint_ttl_seconds"])
                sampler_path = (await save.result_async()).path
                checkpoint = {"epoch": epoch + 1, "state_path": resume_path, "sampler_path": sampler_path, "saved_at": now()}
                state["checkpoints"].append(checkpoint)
                write_json(run_dir / "run.json", state)
                sampler = await service.create_sampling_client_async(model_path=sampler_path)
                metrics = await evaluate(sampler, tokenizer, validation, config, run_dir / f"epoch-{epoch+1}-validation.jsonl")
                key = selection_key(metrics)
                if best_key is None or key > best_key:
                    best_key = key
                    state["selected_checkpoint"] = checkpoint
                write_json(run_dir / "run.json", state)
            chosen = await service.create_sampling_client_async(model_path=state["selected_checkpoint"]["sampler_path"])
            await evaluate(chosen, tokenizer, test, config, run_dir / "finetuned-test.jsonl")
            await evaluate(chosen, tokenizer, [demo_case()], config, run_dir / "finetuned-demo.jsonl")
            state["status"] = "completed"
        except BaseException as exc:
            state["status"] = "failed"
            state["error_type"] = type(exc).__name__
            raise
        finally:
            state["ended_at"] = now()
            write_json(run_dir / "run.json", state)
            if state.get("session_id"):
                await billing_snapshot(service, run_dir, state["started_at"], state["session_id"])
    from .report import generate_report
    generate_report(run_dir)


async def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=["prepare", "preflight", "plan", "run", "report", "billing"])
    parser.add_argument("--config", type=Path, default=HERE / "config.json")
    parser.add_argument("--output", type=Path)
    parser.add_argument("--run-dir", type=Path)
    parser.add_argument("--max-estimated-usd", type=float)
    args = parser.parse_args()
    # Only this optional experiment reads .env; never record or print credentials.
    from dotenv import load_dotenv
    load_dotenv(ROOT / ".env")
    if args.command == "prepare":
        print(json.dumps(prepare(), indent=2)); return
    config = config_from(args.config)
    if args.command == "preflight":
        result = await preflight(config)
        if args.output:
            args.output.parent.mkdir(parents=True, exist_ok=True)
            write_json(args.output, result)
        print(json.dumps(result, indent=2)); return
    if args.command == "plan":
        from transformers import AutoTokenizer
        verify_data()
        result = build_plan(config, AutoTokenizer.from_pretrained(config["base_model"], revision=config["tokenizer_revision"]), await pricing(config["base_model"]))
        if args.output:
            args.output.parent.mkdir(parents=True, exist_ok=True)
            write_json(args.output, result)
        print(json.dumps(result, indent=2)); return
    if args.run_dir is None:
        parser.error("--run-dir is required")
    if args.command == "report":
        from .report import generate_report
        generate_report(args.run_dir); return
    if args.command == "billing":
        import tinker
        configure_transport(config)
        state = load(args.run_dir / "run.json")
        with tinker.ServiceClient(display_name="PromiseKeeper usage refresh") as service:
            await billing_snapshot(service, args.run_dir, state["started_at"], state["session_id"])
        return
    if args.max_estimated_usd is None:
        parser.error("run requires --max-estimated-usd; the prize amount is not a spending budget")
    await run(config, args.run_dir, args.max_estimated_usd)


if __name__ == "__main__":
    asyncio.run(main())
