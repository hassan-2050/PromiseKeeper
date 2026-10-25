"""Offline regression checks. Stubbed outputs are never experiment results."""
import asyncio
import json
from types import SimpleNamespace

import pytest

from app.extraction_contract import non_commitment_quote
from tinker_lab import experiment
from tinker_lab.adapter import make_datum, prompt_tokens
from tinker_lab.evaluation import parse_output, score, validated_items
from tinker_lab.prepare_data import DATA, digest, prepare
from tinker_lab.report import generate_report


def cases(split="test"):
    return experiment.load_cases(split)


def output(case, items=None, **extra):
    values = case["gold"] if items is None else items
    values = [{k: v for k, v in item.items() if k != "match_terms"} for item in values]
    return {"id": case["id"], "raw": json.dumps({"commitments": values}), "stop_reason": "stop",
            "latency_seconds": 1.0, "prompt_tokens": 50, "sample_tokens": 20, "cached_prompt_tokens": 0, **extra}


def test_data_is_reproducible_and_families_are_disjoint(tmp_path):
    manifest = prepare(tmp_path)
    families = []
    for split in ("train", "validation", "test"):
        assert digest(tmp_path / f"{split}.jsonl") == digest(DATA / f"{split}.jsonl")
        assert manifest["splits"][split]["count"] == {"train": 80, "validation": 20, "test": 40}[split]
        families.append(set(manifest["splits"][split]["families"]))
        for case in cases(split):
            assert all(item["evidence"] in case["text"] for item in case["gold"])
    assert not families[0] & families[1]
    assert not families[0] & families[2]
    assert not families[1] & families[2]


def test_known_lexical_filter_limitation_is_retained_in_positive_gold():
    case = next(c for c in cases("train") if c["category"] == "conditional" and "provided" in c["text"])
    assert len(case["gold"]) == 1
    assert non_commitment_quote(case["gold"][0]["evidence"])
    # Existing production behavior wrongly treats 'provided' as completed work.
    # Keep the positive label and make the limitation visible, rather than
    # removing a hard example or changing the production filter for the benchmark.
    assert validated_items(case["gold"], case) == []


def test_multiple_predictions_are_scored_individually_and_not_reused():
    case = next(c for c in cases() if c["category"] == "multiple")
    items = [case["gold"][0], case["gold"][0]]
    raw = score([case], [output(case, items)], pipeline=False)
    assert (raw["tp"], raw["fp"], raw["fn"]) == (1, 1, 1)
    pipeline = score([case], [output(case, items)])
    assert (pipeline["tp"], pipeline["fp"], pipeline["fn"]) == (1, 0, 1)
    assert pipeline["recall"] == .5
    assert pipeline["owner_accuracy"] == .5


def test_wrong_claim_is_not_a_true_positive_even_with_literal_evidence():
    case = cases()[0]
    item = dict(case["gold"][0], claim="invent a different task")
    result = score([case], [output(case, [item])])
    assert (result["tp"], result["fp"], result["fn"]) == (0, 1, 1)


def test_invalid_and_truncated_outputs_are_not_silently_valid_empty_answers():
    positive = cases()[0]
    for row in (output(positive, raw="not JSON"), output(positive, stop_reason="length"),
                output(positive, raw='{"commitments":[{"claim":"x"}]}')):
        result = score([positive], [row])
        assert result["output_validity"] == 0
        assert result["fn"] == 1
    assert parse_output('{"commitments":{}}') == ([], False)


def test_pipeline_defaults_missing_action_like_ollama_but_reports_raw_invalidity():
    case = cases()[0]
    item = {k: v for k, v in case["gold"][0].items() if k != "action"}
    row = output(case, [item])
    raw = score([case], [row], pipeline=False)
    pipeline = score([case], [row])
    assert raw["output_validity"] == pipeline["output_validity"] == 0
    assert raw["tp"] == 0
    assert pipeline["tp"] == 1 and pipeline["fp"] == pipeline["fn"] == 0
    assert pipeline["per_case"][0]["accepted"][0]["action"] == "Review this commitment"


def test_invalid_quotes_and_non_commitments_remain_filtered():
    case = cases()[0]
    item = dict(case["gold"][0], evidence="A fabricated quote")
    result = score([case], [output(case, [item])])
    assert result["raw_quote_substring_rate"] == 0
    assert result["tp"] == 0
    negative = next(c for c in cases() if c["category"] == "refusal")
    refused = dict(case["gold"][0], evidence="I will not send it.")
    negative = dict(negative, text=refused["evidence"])
    assert validated_items([refused], negative) == []


def test_wrong_owner_and_date_are_counted_and_unknown_owner_is_not_invented():
    case = next(c for c in cases() if c["category"] == "deadline" and c["gold"][0]["deadline"])
    item = dict(case["gold"][0], owner="Wrong speaker", deadline=None)
    result = score([case], [output(case, [item])])
    assert result["tp"] == 1
    assert result["owner_accuracy"] == result["known_date_accuracy"] == 0
    case = next(c for c in cases() if c["category"] == "ambiguous_owner")
    item = dict(case["gold"][0], owner="Invented name")
    assert score([case], [output(case, [item])])["owner_accuracy"] == 0


def test_pipeline_resolves_only_anchored_relative_dates():
    case = next(c for c in cases("train") if c["category"] == "deadline" and c["source_timestamp"])
    item = dict(case["gold"][0], deadline="tomorrow")
    assert validated_items([item], case)[0]["deadline"] == "2026-10-26"
    assert validated_items([item], dict(case, source_timestamp=None))[0]["deadline"] is None


def test_missing_or_duplicate_results_cannot_make_a_complete_report():
    case = cases()[0]
    with pytest.raises(ValueError, match="every case"):
        score([case], [])
    with pytest.raises(ValueError, match="every case"):
        score([case], [output(case), output(case)])


class Tokenizer:
    def apply_chat_template(self, messages, tokenize=True, add_generation_prompt=False, **kwargs):
        text = "".join(f"<{m['role']}>{m['content']}<end>" for m in messages)
        if add_generation_prompt:
            text += "<assistant>"
        return self.encode(text) if tokenize else text

    def encode(self, text, **kwargs):
        return [ord(c) for c in text]


def test_sft_masks_prompt_and_shifts_targets_to_next_tokens():
    pytest.importorskip("tinker")
    tokenizer = Tokenizer()
    case = cases("train")[0]
    datum = make_datum(tokenizer, case)
    prefix = prompt_tokens(tokenizer, case)
    weights = datum.loss_fn_inputs["weights"].tolist()
    targets = datum.loss_fn_inputs["target_tokens"].tolist()
    assert len(weights) == len(targets) == datum.model_input.length
    assert weights[:len(prefix)-1] == [0.0] * (len(prefix)-1)
    assert weights[len(prefix)-1:] == [1.0] * (len(weights)-len(prefix)+1)
    assert targets[:len(prefix)-1] == prefix[1:]


def test_no_access_preflight_is_honest_and_never_creates_paid_clients(monkeypatch):
    pytest.importorskip("tinker")
    monkeypatch.setattr("tinker.auth.tinker_has_credentials", lambda: False)
    async def price(model):
        return {"model": model}
    monkeypatch.setattr(experiment, "pricing", price)
    result = asyncio.run(experiment.preflight({"base_model": "Qwen/Qwen3-8B"}))
    assert result["status"] == "access_required"
    assert result["account_models"] is result["account_credits_usd"] is None
    assert result["training_run"] == "not_started"


def test_preflight_timeout_preserves_credential_status_and_never_trains(monkeypatch):
    pytest.importorskip("tinker")
    monkeypatch.setattr("tinker.auth.tinker_has_credentials", lambda: True)
    async def price(model): return {"model": model}
    async def timeout(): raise experiment.httpx.ReadTimeout("Synthetic timeout")
    monkeypatch.setattr(experiment, "pricing", price)
    monkeypatch.setattr(experiment, "fetch_capabilities", timeout)
    result = asyncio.run(experiment.preflight({"base_model": "Qwen/Qwen3-8B"}))
    assert result["status"] == "connection_timeout"
    assert result["credentials_available"] is True
    assert result["training_run"] == "not_started"


def test_report_refuses_pending_experiment(tmp_path):
    (tmp_path / "run.json").write_text('{"status":"running"}')
    (tmp_path / "plan.json").write_text('{}')
    with pytest.raises(ValueError, match="completed real run"):
        generate_report(tmp_path)


def test_full_workflow_selects_on_validation_and_tests_selected_epoch_once(monkeypatch, tmp_path):
    tinker = pytest.importorskip("tinker")
    transformers = pytest.importorskip("transformers")
    events = []

    class Future:
        def __init__(self, value): self.value = value
        async def result_async(self): return self.value

    class Training:
        async def forward_backward_async(self, batch, loss):
            events.append(("train",))
            outputs = [{"logprobs": SimpleNamespace(tolist=lambda d=d: [-.1] * d.model_input.length)} for d in batch]
            return Future(SimpleNamespace(loss_fn_outputs=outputs, metrics={}))
        async def optim_step_async(self, params): return Future(None)
        async def save_state_async(self, name, **kwargs): return Future(SimpleNamespace(path=f"tinker://stub/state/{name}"))
        async def save_weights_for_sampler_async(self, name, **kwargs): return Future(SimpleNamespace(path=f"tinker://stub/sampler_weights/{name}"))

    class Service:
        def __init__(self, **kwargs): pass
        def __enter__(self): return self
        def __exit__(self, *args): pass
        def get_console_url(self): return "https://tinker.thinkingmachines.ai/sessions/stub-session"
        async def create_sampling_client_async(self, base_model=None, model_path=None):
            return SimpleNamespace(role="baseline" if base_model else model_path.rsplit("/", 1)[-1])
        async def create_lora_training_client_async(self, **kwargs): return Training()

    price = {"rates_per_million_usd": {"train": .44, "prefill": .195, "cached_prefill": .039, "sample": .60}}
    async def access(config): return {"status": "ready_for_budget_review", "pricing": price}
    async def sample(client, tokenizer, case, config):
        events.append(("sample", client.role, case["split"] if "split" in case else "demo", case["id"]))
        row = output(case, [] if client.role in {"baseline", "epoch-1"} else None)
        if client.role == "epoch-3":
            items = json.loads(row["raw"])["commitments"]
            for item in items: item["owner"] = "Wrong speaker"
            row["raw"] = json.dumps({"commitments": items})
        return row
    async def billing(*args): pass
    monkeypatch.setattr(experiment, "preflight", access)
    monkeypatch.setattr(experiment, "sample_case", sample)
    monkeypatch.setattr(experiment, "billing_snapshot", billing)
    monkeypatch.setattr(tinker, "ServiceClient", Service)
    monkeypatch.setattr(transformers.AutoTokenizer, "from_pretrained", lambda *a, **k: Tokenizer())
    config = experiment.config_from(experiment.HERE / "config.json")
    folder = tmp_path / "stubbed-offline-run"
    asyncio.run(experiment.run(config, folder, 100))
    state = json.loads((folder / "run.json").read_text())
    assert state["status"] == "completed"
    assert state["selected_checkpoint"]["epoch"] == 2
    first_training = next(i for i, event in enumerate(events) if event[0] == "train")
    baseline_tests = [i for i, e in enumerate(events) if e[:3] == ("sample", "baseline", "test")]
    assert len(baseline_tests) == 40 and max(baseline_tests) < first_training
    final_tests = [e for e in events if e[0] == "sample" and e[2] == "test" and e[1] != "baseline"]
    assert len(final_tests) == 40 and all(e[1] == "epoch-2" for e in final_tests)
    assert (folder / "comparison.html").exists()
    original_test_hash = digest(folder / "finetuned-test.jsonl")
    asyncio.run(experiment.finalize(config, folder))
    finalized = json.loads((folder / "run.json").read_text())
    assert finalized["selection_scoring_version"] == 2
    assert finalized["selected_checkpoint"]["epoch"] == 2
    assert digest(folder / "finetuned-test.jsonl") == original_test_hash
    assert (folder / "epoch-2-validation.metrics-v2.json").exists()
    from app import tinker_runtime
    monkeypatch.setenv("TINKER_VERIFIED_RUN", str(folder))
    monkeypatch.setattr("tinker.auth.tinker_has_credentials", lambda: True)
    assert tinker_runtime.verified_configuration()[1]["selected_checkpoint"]["epoch"] == 2
    comparison_path = folder / "comparison.json"
    comparison = json.loads(comparison_path.read_text())
    comparison["metrics"]["pipeline"]["baseline"]["f1"] = 1
    comparison["metrics"]["pipeline"]["finetuned"]["f1"] = .9
    comparison_path.write_text(json.dumps(comparison))
    with pytest.raises(ValueError, match="regresses"):
        tinker_runtime.verified_configuration()
    monkeypatch.setenv("TINKER_SYNTHETIC_PREVIEW", "true")
    assert tinker_runtime.verified_configuration()[1]["preview_only"] is True
    tinker_runtime.validate_preview_source(cases()[0]["text"], folder)
    with pytest.raises(tinker_runtime.PreviewSourceError, match="frozen synthetic"):
        tinker_runtime.validate_preview_source("Private unseen notes must not be uploaded", folder)
    with pytest.raises(ValueError, match="already exists"):
        asyncio.run(experiment.run(config, folder, 100))
