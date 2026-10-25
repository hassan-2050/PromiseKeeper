"""Deterministic commitment-level scoring; no model-as-judge or tuned thresholds."""
import json
import math
import re
from datetime import datetime

from app.extraction_contract import ExtractedCommitment, non_commitment_quote, resolve_deadline_text


def norm(value):
    return re.sub(r"[^a-z0-9]+", " ", (value or "").casefold()).strip()


def parse_output(raw):
    try:
        value = json.loads(raw)
        if not isinstance(value, dict) or not isinstance(value.get("commitments"), list):
            return [], False
        return [ExtractedCommitment.model_validate(item).model_dump() for item in value["commitments"]], True
    except (ValueError, TypeError):
        return [], False


def validated_items(items, case):
    timestamp = datetime.fromisoformat(case["source_timestamp"]) if case.get("source_timestamp") else None
    accepted = {}
    for original in items:
        item = dict(original)
        if item["evidence"] not in case["text"] or non_commitment_quote(item["evidence"]):
            continue
        item["deadline"] = resolve_deadline_text(item["deadline"], timestamp)
        key = (norm(item["claim"]), norm(item["owner"]), norm(item["recipient"]), norm(item["deadline"]))
        accepted.setdefault(key, item)
    return list(accepted.values())


def matches(item, gold, text):
    # Require both an annotated evidence overlap and the authored task nouns in
    # the claim. This is a lexical task/span proxy, not a semantic entailment score.
    evidence = item["evidence"]
    return (evidence in text and (gold["evidence"] in evidence or evidence in gold["evidence"])
            and all(term in norm(item["claim"]).split() for term in gold["match_terms"]))


def pair_items(items, gold, text):
    # Maximum bipartite matching avoids inflating recall with duplicate predictions
    # or depending on prediction order in multi-commitment transcripts.
    occupied = {}

    def visit(pred_index, seen):
        for gold_index, expected in enumerate(gold):
            if gold_index in seen or not matches(items[pred_index], expected, text):
                continue
            seen.add(gold_index)
            if gold_index not in occupied or visit(occupied[gold_index], seen):
                occupied[gold_index] = pred_index
                return True
        return False

    for index in range(len(items)):
        visit(index, set())
    return occupied


def score(cases, rows, pipeline=True):
    by_id = {row["id"]: row for row in rows}
    if len(by_id) != len(rows) or set(by_id) != {c["id"] for c in cases}:
        raise ValueError("Results must contain every case exactly once")
    tp = fp = fn = owner_ok = date_ok = owner_known_ok = date_known_ok = 0
    owner_n = date_n = valid = errors = quotes = quote_ok = 0
    category = {}
    latency = []
    details = []
    for case in cases:
        row = by_id[case["id"]]
        items, schema_ok = parse_output(row.get("raw", ""))
        schema_ok = schema_ok and row.get("stop_reason") == "stop" and not row.get("error")
        valid += int(schema_ok)
        errors += int(bool(row.get("error")))
        quotes += len(items)
        quote_ok += sum(item["evidence"] in case["text"] for item in items)
        if row.get("latency_seconds") is not None:
            latency.append(row["latency_seconds"])
        predicted = validated_items(items, case) if pipeline else items
        if not schema_ok:
            predicted = []
        gold = case["gold"]
        pairs = pair_items(predicted, gold, case["text"])
        case_tp, case_fp, case_fn = len(pairs), len(predicted) - len(pairs), len(gold) - len(pairs)
        # An invalid response is separately visible in output_validity. It cannot
        # contribute a true positive, but is not a fabricated commitment either.
        tp += case_tp; fp += case_fp; fn += case_fn
        counts = category.setdefault(case["category"], {"cases": 0, "tp": 0, "fp": 0, "fn": 0})
        for key, amount in (("cases", 1), ("tp", case_tp), ("fp", case_fp), ("fn", case_fn)):
            counts[key] += amount
        for index, expected in enumerate(gold):
            actual = predicted[pairs[index]] if index in pairs else None
            owner_match = actual is not None and norm(actual["owner"]) == norm(expected["owner"])
            date_match = actual is not None and actual["deadline"] == expected["deadline"]
            owner_ok += int(owner_match); date_ok += int(date_match)
            if expected["owner"] is not None:
                owner_n += 1; owner_known_ok += int(owner_match)
            if expected["deadline"] is not None:
                date_n += 1; date_known_ok += int(date_match)
        details.append({"id": case["id"], "tp": case_tp, "fp": case_fp, "fn": case_fn,
                        "output_valid": schema_ok, "accepted": predicted})
    n_gold = sum(len(case["gold"]) for case in cases)
    ratio = lambda a, b: a / b if b else None
    precision, recall = ratio(tp, tp + fp), ratio(tp, tp + fn)
    f1 = 2 * tp / (2 * tp + fp + fn) if 2 * tp + fp + fn else None
    return {"cases": len(cases), "tp": tp, "fp": fp, "fn": fn,
            "precision": precision, "recall": recall, "f1": f1,
            "owner_accuracy": ratio(owner_ok, n_gold), "owner_correct": owner_ok, "gold_commitments": n_gold,
            "known_owner_accuracy": ratio(owner_known_ok, owner_n), "known_owner_eligible": owner_n,
            "date_accuracy": ratio(date_ok, n_gold), "date_correct": date_ok,
            "known_date_accuracy": ratio(date_known_ok, date_n), "known_date_eligible": date_n,
            "output_validity": ratio(valid, len(cases)), "valid_outputs": valid, "request_errors": errors,
            "raw_quote_substring_rate": ratio(quote_ok, quotes),
            "latency_mean_seconds": ratio(sum(latency), len(latency)),
            "latency_p95_seconds": sorted(latency)[max(0, math.ceil(len(latency) * .95) - 1)] if latency else None,
            "per_category": category, "per_case": details}
