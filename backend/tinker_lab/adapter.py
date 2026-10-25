"""Experimental remote sampler. The application does not select this adapter.

Only authored synthetic input is allowed by the experiment CLI. Connecting this
to real imports needs an explicit cloud-data product flow and checkpoint review.
"""
import json
import time
from datetime import datetime

from app.extraction_contract import build_prompt
from .evaluation import parse_pipeline_output, validated_items


def prompt_tokens(tokenizer, case):
    timestamp = datetime.fromisoformat(case["source_timestamp"]) if case.get("source_timestamp") else None
    return tokenizer.apply_chat_template(
        [{"role": "user", "content": build_prompt(case["text"], timestamp)}],
        tokenize=True, add_generation_prompt=True, enable_thinking=False, return_dict=False)


def make_datum(tokenizer, case):
    import tinker
    timestamp = datetime.fromisoformat(case["source_timestamp"]) if case.get("source_timestamp") else None
    answer = {"commitments": [{k: v for k, v in item.items() if k != "match_terms"} for item in case["gold"]]}
    messages = [{"role": "user", "content": build_prompt(case["text"], timestamp)},
                {"role": "assistant", "content": json.dumps(answer, ensure_ascii=False)}]
    prompt_text = tokenizer.apply_chat_template(messages[:1], tokenize=False, add_generation_prompt=True, enable_thinking=False)
    full_text = tokenizer.apply_chat_template(messages, tokenize=False, enable_thinking=False)
    if not full_text.startswith(prompt_text):
        raise ValueError("Tokenizer chat template is not prefix-compatible with assistant-only loss")
    prefix = tokenizer.encode(prompt_text, add_special_tokens=False)
    completion = tokenizer.encode(full_text[len(prompt_text):], add_special_tokens=False)
    tokens = prefix + completion
    weights = [0.0] * len(prefix) + [1.0] * len(completion)
    return tinker.Datum(model_input=tinker.ModelInput.from_ints(tokens[:-1]),
                        loss_fn_inputs={"target_tokens": tokens[1:], "weights": weights[1:]})


async def sample_case(client, tokenizer, case, config):
    import tinker
    tokens = prompt_tokens(tokenizer, case)
    started = time.perf_counter()
    result = await client.sample_async(
        prompt=tinker.ModelInput.from_ints(tokens), num_samples=1,
        sampling_params=tinker.SamplingParams(max_tokens=config["max_tokens"],
                                              temperature=config["temperature"], seed=config["seed"]))
    elapsed = time.perf_counter() - started
    sequence = result.sequences[0]
    return {"id": case["id"], "raw": tokenizer.decode(sequence.tokens, skip_special_tokens=True),
            "stop_reason": sequence.stop_reason, "latency_seconds": elapsed,
            "prompt_tokens": len(tokens), "sample_tokens": len(sequence.tokens),
            "cached_prompt_tokens": result.prompt_cache_hit_tokens}


async def extract_experimental(client, tokenizer, case, config):
    row = await sample_case(client, tokenizer, case, config)
    items, valid = parse_pipeline_output(row["raw"])
    if not valid or row["stop_reason"] != "stop":
        raise ValueError("Tinker returned invalid or truncated extraction output")
    return validated_items(items, case)
