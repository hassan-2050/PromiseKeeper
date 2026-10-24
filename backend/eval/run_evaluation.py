"""Measure extraction against the labeled synthetic corpus using local Ollama."""
import asyncio
import json
import re
import sys
import httpx
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app.main import OLLAMA_MODEL, extract_local

ROOT = Path(__file__).resolve().parents[2]
CASES = [json.loads(line) for line in (ROOT / "backend/eval/cases.jsonl").read_text(encoding="utf-8").splitlines()]
norm = lambda value: re.sub(r"[^a-z0-9]+", " ", (value or "").casefold()).strip()

async def main():
    tp = fp = fn = owner_ok = owner_n = date_ok = date_n = quote_ok = quote_n = 0
    async with httpx.AsyncClient(timeout=5) as client:
        tags = (await client.get("http://localhost:11434/api/tags")).json().get("models", [])
    model_digest = next((m.get("digest") for m in tags if m.get("name", "").startswith(OLLAMA_MODEL)), None)
    category = {}
    per_case = []
    for case in CASES:
        output = await extract_local(case["text"], None)
        gold = case["gold"]
        predicted = bool(output)
        row = category.setdefault(case["category"], {"n": 0, "positive_gold": 0, "tp": 0, "fp": 0, "fn": 0, "owner_exact": 0, "owner_eligible": 0, "date_exact": 0, "date_eligible": 0})
        row["n"] += 1
        row["positive_gold"] += int(gold["commitment"])
        row["tp"] += int(predicted and gold["commitment"])
        row["fp"] += int(predicted and not gold["commitment"])
        row["fn"] += int(not predicted and gold["commitment"])
        tp += int(predicted and gold["commitment"])
        fp += int(predicted and not gold["commitment"])
        fn += int(not predicted and gold["commitment"])
        if gold["commitment"]:
            if gold["owner"] is not None:
                owner_n += 1; row["owner_eligible"] += 1; match = predicted and norm(output[0].get("owner")) == norm(gold["owner"])
                owner_ok += int(match); row["owner_exact"] += int(match)
            if gold["deadline"] is not None:
                date_n += 1; row["date_eligible"] += 1; match = predicted and norm(output[0].get("deadline")) == norm(gold["deadline"])
                date_ok += int(match); row["date_exact"] += int(match)
        quote_n += len(output)
        quote_ok += sum(1 for item in output if item.get("evidence") and item["evidence"] in case["text"])
        per_case.append({"id": case["id"], "category": case["category"], "expected_commitment": gold["commitment"], "predicted_count": len(output), "predictions": [{"claim": item["claim"], "owner": item.get("owner"), "deadline": item.get("deadline"), "evidence": item["evidence"]} for item in output]})
        print(f"[{case['id']}] {case['category']}: {'commitment' if predicted else 'none'}", flush=True)
    result = {
      "run_type": "measured real local inference on synthetic authored examples",
      "synthetic": True, "cases": len(CASES), "model": OLLAMA_MODEL, "model_digest": model_digest,
      "completed_at_utc": datetime.now(timezone.utc).isoformat(),
      "commitment_classification": {"tp": tp, "fp": fp, "fn": fn, "precision": tp / (tp + fp) if tp + fp else None, "recall": tp / (tp + fn) if tp + fn else None},
      "owner_exact_accuracy": {"correct": owner_ok, "eligible": owner_n, "accuracy": owner_ok / owner_n if owner_n else None},
      "deadline_exact_accuracy": {"correct": date_ok, "eligible": date_n, "accuracy": date_ok / date_n if date_n else None},
      "accepted_quote_substring_rate": {"valid": quote_ok, "accepted": quote_n, "rate": quote_ok / quote_n if quote_n else None},
      "per_category": category,
      "per_case": per_case,
      "limitations": ["Synthetic and small corpus; not representative of real conversation.", "Claim entailment is not scored; quote-substring validation proves provenance, not entailment.", "Relative dates without a source timestamp remain unresolved by design."]
    }
    path = ROOT / "docs" / "eval_run.json"
    path.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2))

asyncio.run(main())
