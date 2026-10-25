"""Build a reviewable comparison from complete, frozen, actual run artifacts."""
import html
import json
from pathlib import Path

from .evaluation import score
from .prepare_data import digest, write_json

METRICS = [("Precision", "precision"), ("Recall", "recall"), ("F1", "f1"),
           ("Owner accuracy (all gold commitments)", "owner_accuracy"),
           ("Owner accuracy (known owners)", "known_owner_accuracy"),
           ("Date accuracy (all gold commitments)", "date_accuracy"),
           ("Date accuracy (known dates)", "known_date_accuracy"),
           ("Output validity", "output_validity"), ("Raw quote substring rate", "raw_quote_substring_rate"),
           ("Mean latency, seconds", "latency_mean_seconds"), ("P95 latency, seconds", "latency_p95_seconds")]


def read(path):
    return json.loads(path.read_text(encoding="utf-8"))


def rows(path):
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]


def fmt(value):
    return "unavailable" if value is None else f"{value:.4f}"


def generate_report(run_dir):
    run_dir = Path(run_dir)
    state, plan = read(run_dir / "run.json"), read(run_dir / "plan.json")
    if state["status"] != "completed" or not state.get("selected_checkpoint"):
        raise ValueError("A completed real run and checkpoint are required; pending metrics cannot be published")
    for split, info in plan["dataset_manifest"]["splits"].items():
        if digest(run_dir / f"{split}.jsonl") != info["sha256"]:
            raise ValueError("Frozen dataset artifact has changed")
    cases = rows(run_dir / "test.jsonl")
    predictions = {name: rows(run_dir / f"{name}-test.jsonl") for name in ("baseline", "finetuned")}
    metrics = {stage: {name: score(cases, values, pipeline=stage == "pipeline")
                       for name, values in predictions.items()} for stage in ("raw", "pipeline")}
    write_json(run_dir / "comparison.json", {"synthetic": True, "run": state, "metrics": metrics,
               "test_sha256": digest(run_dir / "test.jsonl"), "actual_invoice_cost_usd": None})
    parts = ["# PromiseKeeper: measured Tinker comparison", "",
             "Authored synthetic held-out set. These results do not establish real-world accuracy or contest eligibility.", "",
             f"Base model: `{plan['config']['base_model']}`. Checkpoint: `{state['selected_checkpoint']['sampler_path']}`.",
             f"Test SHA-256: `{digest(run_dir / 'test.jsonl')}`.", ""]
    tables = []
    for stage, values in metrics.items():
        parts += [f"## {'Raw model output' if stage == 'raw' else 'After existing evidence, date and duplicate checks'}", "",
                  "| Metric | Baseline | Fine-tuned |", "| --- | ---: | ---: |"]
        table = []
        for label, key in METRICS:
            a, b = fmt(values["baseline"][key]), fmt(values["finetuned"][key])
            parts.append(f"| {label} | {a} | {b} |")
            table.append(f"<tr><th scope='row'>{html.escape(label)}</th><td>{a}</td><td>{b}</td></tr>")
        parts += ["", f"TP / FP / FN: baseline {values['baseline']['tp']} / {values['baseline']['fp']} / {values['baseline']['fn']}; "
                  f"fine-tuned {values['finetuned']['tp']} / {values['finetuned']['fp']} / {values['finetuned']['fn']}.", ""]
        tables.append(f"<h2>{stage.title()} results</h2><table><thead><tr><th>Metric</th><th>Baseline</th><th>Fine-tuned</th></tr></thead><tbody>{''.join(table)}</tbody></table>")
    training_tokens = sum(row["tokens"] for row in rows(run_dir / "training.jsonl"))
    rates = plan["pricing"]["rates_per_million_usd"]
    usage = {"training": {"tokens": training_tokens, "rate_card_estimate_usd": training_tokens * rates["train"] / 1e6}}
    for path in sorted(run_dir.glob("*.jsonl")):
        if path.name in {"training.jsonl", "train.jsonl", "validation.jsonl", "test.jsonl"}:
            continue
        values = rows(path)
        prompt = sum(v["prompt_tokens"] for v in values)
        cached = sum(v["cached_prompt_tokens"] for v in values)
        sample = sum(v["sample_tokens"] for v in values)
        usage[path.stem] = {"prompt_tokens": prompt, "cached_prompt_tokens": cached, "sample_tokens": sample,
                            "rate_card_estimate_usd": ((prompt-cached)*rates["prefill"] + cached*rates["cached_prefill"] + sample*rates["sample"]) / 1e6}
    write_json(run_dir / "token-usage.json", usage)
    costs = ["## Costs", "", "Measured token counts and rate-card estimates are in `token-usage.json`. "
             "Provider-reported session usage is in `billing.json` when available. Gross usage estimates, credits used and invoice amount due are different quantities. "
             "Actual invoice cost: **unavailable** until independently verified. Storage and unassigned billing events are not assumed to be free.", "",
             f"Training tokens: {training_tokens}; training rate-card estimate: ${usage['training']['rate_card_estimate_usd']:.6f}.", ""]
    parts += costs + ["## Scoring limits", "", "One-to-one task-noun and annotated-evidence overlap matching is a lexical proxy. "
             "It does not prove semantic entailment. Owner/date denominators include missed gold commitments and unresolved null fields; known-only scores are also shown. "
             "Invalid/truncated responses count against output validity and cannot earn true positives. Schema validity, raw quotes and pipeline metrics are separate. "
             "Latency measures each remote sample call, including server waiting, after client/tokenizer setup. "
             "Check the raw outputs, errors and per-category counts before interpreting any change.", "",
             "## Fixed synthetic demo", ""]
    demo = read(run_dir / "demo.json")
    parts += ["```text", demo["text"], "```", ""]
    demo_html = [f"<h2>Fixed synthetic demo</h2><pre>{html.escape(demo['text'])}</pre>"]
    for name in ("baseline", "finetuned"):
        result = rows(run_dir / f"{name}-demo.jsonl")[0]
        parts += [f"### {name.title()}", "", "```text", result["raw"], "```", ""]
        demo_html.append(f"<details open><summary>{name.title()} actual output</summary><pre>{html.escape(result['raw'])}</pre></details>")
    parts += ["The demo is fixed before inference. If the baseline is perfect or tuning makes it worse, show that result honestly. "
              "A recorded review-interface journey and screenshots remain separate deliverables; this report is not evidence of that capture.", ""]
    (run_dir / "comparison.md").write_text("\n".join(parts), encoding="utf-8")
    page = ("<!doctype html><html lang='en'><meta charset='utf-8'><meta name='viewport' content='width=device-width,initial-scale=1'>"
            "<title>PromiseKeeper · Tinker experiment</title><style>body{margin:3rem auto;max-width:960px;padding:0 1.2rem;background:#101b17;color:#e4f5eb;font:17px/1.6 system-ui}"
            "h1,h2,summary{color:#a2e5bf}table{border-collapse:collapse;width:100%;margin-bottom:2rem}td,th{border-bottom:1px solid #456353;padding:.6rem;text-align:left}"
            "pre{white-space:pre-wrap;overflow-wrap:anywhere;background:#192b22;padding:1rem;border-radius:8px}summary{cursor:pointer}a{color:#a2e5bf}</style>"
            "<h1>PromiseKeeper · Tinker experiment</h1><p>Measured results on a small authored synthetic held-out set. Review required.</p>"
            + f"<p>Model: {html.escape(plan['config']['base_model'])}<br>Checkpoint: {html.escape(state['selected_checkpoint']['sampler_path'])}</p>"
            + "".join(tables) + "<h2>Costs</h2><p>Actual invoice cost unavailable. See token-usage.json for measured tokens and rate-card estimates, and billing.json for provider usage.</p>"
            + "".join(demo_html) + "<p>See comparison.md for scoring rules, limitations and provenance. The app continues to use local Ollama.</p></html>")
    (run_dir / "comparison.html").write_text(page, encoding="utf-8")
    return metrics
