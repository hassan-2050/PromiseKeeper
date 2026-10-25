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
    if state.get("selection_scoring_version") != 2:
        raise ValueError("Run needs finalize: rescore validation with the corrected pipeline defaults before reporting")
    for split, info in plan["dataset_manifest"]["splits"].items():
        if digest(run_dir / f"{split}.jsonl") != info["sha256"]:
            raise ValueError("Frozen dataset artifact has changed")
    cases = rows(run_dir / "test.jsonl")
    predictions = {"baseline": rows(run_dir / "baseline-test.jsonl"),
                   "finetuned": rows(run_dir / f"{state.get('final_output_prefix', 'finetuned')}-test.jsonl")}
    metrics = {stage: {name: score(cases, values, pipeline=stage == "pipeline")
                       for name, values in predictions.items()} for stage in ("raw", "pipeline")}
    write_json(run_dir / "comparison.json", {"synthetic": True, "run": state, "metrics": metrics,
               "test_sha256": digest(run_dir / "test.jsonl"), "actual_invoice_cost_usd": None})
    parts = ["# PromiseKeeper: measured Tinker comparison", "",
             "Authored synthetic held-out set. These results do not establish real-world accuracy or contest eligibility.", "",
             f"Base model: `{plan['config']['base_model']}`. Checkpoint: `{state['selected_checkpoint']['sampler_path']}`.",
             f"Test SHA-256: `{digest(run_dir / 'test.jsonl')}`.", ""]
    if state.get("scoring_correction"):
        parts += ["Scoring correction: " + state["scoring_correction"], ""]
    tables = []
    for stage in ("pipeline", "raw"):
        values = metrics[stage]
        parts += [f"## {'Raw model output' if stage == 'raw' else 'After existing evidence, date and duplicate checks'}", "",
                  "| Metric | Baseline | Fine-tuned |", "| --- | ---: | ---: |"]
        table = []
        for label, key in METRICS:
            a, b = fmt(values["baseline"][key]), fmt(values["finetuned"][key])
            parts.append(f"| {label} | {a} | {b} |")
            table.append(f"<tr><th scope='row'>{html.escape(label)}</th><td>{a}</td><td>{b}</td></tr>")
        parts += ["", f"TP / FP / FN: baseline {values['baseline']['tp']} / {values['baseline']['fp']} / {values['baseline']['fn']}; "
                  f"fine-tuned {values['finetuned']['tp']} / {values['finetuned']['fp']} / {values['finetuned']['fn']}.", "",
                  f"Gold commitments: {values['baseline']['gold_commitments']}; known-owner denominator: {values['baseline']['known_owner_eligible']}; known-date denominator: {values['baseline']['known_date_eligible']}.", ""]
        tables.append(f"<h2>{stage.title()} results</h2><table><thead><tr><th>Metric</th><th>Baseline</th><th>Fine-tuned</th></tr></thead><tbody>{''.join(table)}</tbody></table>"
                      f"<p>Denominators: {values['baseline']['gold_commitments']} gold commitments, {values['baseline']['known_owner_eligible']} known owners, {values['baseline']['known_date_eligible']} known dates.</p>")
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
             f"Training tokens: {training_tokens}; training rate-card estimate: ${usage['training']['rate_card_estimate_usd']:.6f}.", "",
             f"All recorded sampling rate-card estimate: ${sum(v['rate_card_estimate_usd'] for k, v in usage.items() if k != 'training'):.6f}; "
             f"training plus recorded sampling: ${sum(v['rate_card_estimate_usd'] for v in usage.values()):.6f}. "
             "Storage and separate live UI preview requests are outside this token total.", ""]
    billing_path = run_dir / "billing.json"
    if billing_path.exists():
        billing = read(billing_path)
        if billing.get("events"):
            gross = sum(event.get("estimated_cost_usd", 0) or 0 for event in billing["events"])
            costs += [f"Provider session usage snapshot ({billing.get('captured_at', 'capture time unavailable')}) "
                      f"reports ${gross:.6f} gross estimated usage. This is not an invoice or verified credit debit.", ""]
    parts += costs + ["## Scoring limits", "", "One-to-one task-noun and annotated-evidence overlap matching is a lexical proxy. "
             "It does not prove semantic entailment. Owner/date denominators include missed gold commitments and unresolved null fields; known-only scores are also shown. "
             "Malformed/truncated JSON cannot earn true positives. Strict raw schema validity is separate from pipeline scoring: the latter supplies the existing adapter's default action text and certainty before validating individual candidates. "
             "Latency measures each remote sample call, including server waiting, after client/tokenizer setup. "
             "Check the raw outputs, errors and per-category counts before interpreting any change.", "",
             "## Fixed synthetic demo", ""]
    demo = read(run_dir / "demo.json")
    parts += ["```text", demo["text"], "```", ""]
    demo_html = [f"<section id='fixed-demo'><h2>Fixed synthetic demo</h2><pre>{html.escape(demo['text'])}</pre>"]
    for name in ("baseline", "finetuned"):
        prefix = state.get("final_output_prefix", "finetuned") if name == "finetuned" else "baseline"
        result = rows(run_dir / f"{prefix}-demo.jsonl")[0]
        parts += [f"### {name.title()}", "", "```text", result["raw"], "```", ""]
        demo_html.append(f"<details open><summary>{name.title()} actual output</summary><pre>{html.escape(result['raw'])}</pre></details>")
    demo_html.append("</section>")
    # An illustrative example is explicitly selected after evaluation. It never
    # changes the frozen metric set or checkpoint selection.
    accepted = {name: {r["id"]: r for r in metrics["pipeline"][name]["per_case"]} for name in predictions}
    example = next((case for case in cases if not case["gold"] and
                    accepted["baseline"][case["id"]]["fp"] > accepted["finetuned"][case["id"]]["fp"]), None)
    illustration_html = ""
    if example:
        actual = {name: next(row for row in values if row["id"] == example["id"]) for name, values in predictions.items()}
        write_json(run_dir / "illustrative-test.json", {"case": example, "outputs": actual,
                   "selection": "First negative test case in frozen order with fewer fine-tuned false positives; selected after evaluation for illustration only."})
        note = "Selected after evaluation to illustrate one reduction in false positives. This is part of the same test set, not an additional benchmark. The full results include regressions."
        parts += ["## Illustrative held-out case", "", note, "", f"Case: `{example['id']}`.", "", "```text", example["text"], "```", ""]
        blocks = [f"<section id='illustration'><h2>Illustrative held-out case</h2><p>{html.escape(note)}</p><pre>{html.escape(example['text'])}</pre>"]
        for name in ("baseline", "finetuned"):
            parts += [f"### {name.title()} actual test output", "", "```text", actual[name]["raw"], "```", ""]
            blocks.append(f"<details open><summary>{name.title()} actual output</summary><pre>{html.escape(actual[name]['raw'])}</pre></details>")
        blocks.append("</section>")
        illustration_html = "".join(blocks)
    parts += ["The fixed synthetic demo was authored before inference. Its raw outputs are separate from the post-evaluation illustrative case. "
              "Screenshots and recordings of the live review interface have their own capture provenance; this report alone does not verify that journey.", ""]
    (run_dir / "comparison.md").write_text("\n".join(parts), encoding="utf-8")
    page = ("<!doctype html><html lang='en'><meta charset='utf-8'><meta name='viewport' content='width=device-width,initial-scale=1'>"
            "<title>PromiseKeeper · Tinker experiment</title><style>body{margin:3rem auto;max-width:960px;padding:0 1.2rem;background:#101b17;color:#e4f5eb;font:17px/1.6 system-ui}"
            "h1,h2,summary{color:#a2e5bf}table{border-collapse:collapse;width:100%;margin-bottom:2rem}td,th{border-bottom:1px solid #456353;padding:.6rem;text-align:left}"
            "pre{white-space:pre-wrap;overflow-wrap:anywhere;background:#192b22;padding:1rem;border-radius:8px;font-size:14px;line-height:1.35}summary{cursor:pointer}a{color:#a2e5bf}</style>"
            "<h1>PromiseKeeper · Tinker experiment</h1><p>Measured results on a small authored synthetic held-out set. Review required.</p>"
            + f"<p>Model: {html.escape(plan['config']['base_model'])}<br>Checkpoint: {html.escape(state['selected_checkpoint']['sampler_path'])}</p>"
            + "".join(tables) + "<h2>Costs</h2><p>Actual invoice cost unavailable. See token-usage.json for measured tokens and rate-card estimates, and billing.json for provider usage.</p>"
            + illustration_html + "".join(demo_html) + "<p>See comparison.md for scoring rules, limitations and provenance. The app continues to use local Ollama.</p></html>")
    (run_dir / "comparison.html").write_text(page, encoding="utf-8")
    return metrics
