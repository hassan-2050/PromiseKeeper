"""Reproducible authored synthetic starter set with split-specific template families.

No real source documents or the existing development corpus are training inputs.
Family membership is authored before inference, never assigned from model scores.
"""
import hashlib
import json
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
DATA = HERE / "data"


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_json(path, value):
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n", encoding="utf-8", newline="\n")


def families():
    # Each list is [two training families, validation family, two test families].
    # [[...]] identifies the annotated evidence span and is removed from the source.
    return {
        "explicit": [
            "{owner}: [[I'll send the {task} to {other}.]]",
            "{other}: Is the {task} ready?\n{owner}: [[I will send the {task} after lunch.]]",
            "{owner}: [[Count on me to send the {task}.]]\n{other}: Thank you.",
            "{other}: The {task} is still missing.\n{owner}: [[You have my word: I will send the {task}.]]",
            "{owner}: [[I'm committing to send the {task}.]]\n{other}: Put that in the minutes.",
        ],
        "implicit": [
            "{owner}: [[The {task} will be in your inbox tomorrow.]]",
            "{other}: Who is handling the {task}?\n{owner}: [[Leave the {task} with me.]]",
            "{owner}: [[Consider the {task} my responsibility from here.]]",
            "{other}: We have no one on the {task}.\n{owner}: [[The {task} is on my plate now.]]",
            "{other}: Can someone take the {task}?\n{owner}: [[You've got a volunteer for the {task}: me.]]",
        ],
        "conditional": [
            "{owner}: [[If legal signs off, I'll send the {task}.]]",
            "{owner}: [[I'll send the {task} provided the budget is approved.]]",
            "{other}: We need the {task}.\n{owner}: [[Once access is restored, I will send the {task}.]]",
            "{owner}: [[Unless the launch is cancelled, I will send the {task}.]]",
            "{owner}: [[If the committee votes yes, the {task} is mine to send.]]",
        ],
        "refusal": [
            "{owner}: I won't send the {task}; please find someone else.",
            "{owner}: No, I cannot take responsibility for the {task}.",
            "{other}: Would you send the {task}?\n{owner}: I'm declining that request.",
            "{owner}: Please remove my name from the {task}. I am not agreeing to send it.",
            "{other}: Can we count on you for the {task}?\n{owner}: Not this time. My answer is no.",
        ],
        "completed": [
            "{owner}: I sent the {task} yesterday; check your inbox.",
            "{owner}: The {task} was delivered this morning. No further action.",
            "{other}: What about the {task}?\n{owner}: Already taken care of, nothing pending.",
            "{owner}: For the record, the {task} went out last night. That closes it.",
            "{owner}: The tracker marks the {task} complete. It reached everyone an hour ago.",
        ],
        "hypothetical": [
            "{owner}: I could send the {task} if I had spare time, but I'm not committing.",
            "{owner}: Imagine if I were to send the {task}. Just a thought experiment.",
            "{other}: In a fictional scenario, who would send the {task}?\n{owner}: Maybe me.",
            "{owner}: Suppose I had agreed to send the {task}. That would be different; I haven't.",
            "{owner}: Sending the {task} is one possible option. No decision or assignment yet.",
        ],
        "ambiguous_owner": [
            "{owner}: [[Someone needs to send the {task}.]]",
            "{other}: [[The {task} must go out, but no owner has been chosen.]]",
            "{owner}: [[We still have an obligation to send the {task}; assignment is unresolved.]]",
            "{other}: [[Sending the {task} is mandatory. We haven't decided who does it.]]",
            "{owner}: [[The {task} needs an accountable sender. That seat is vacant.]]",
        ],
        "deadline": [
            "{owner}: [[I will send the {task} on {date}.]]",
            "{owner}: [[I'll send the {task} tomorrow.]]",
            "{owner}: [[The {task} will be in your inbox in 2 days.]]",
            "{other}: Do we have a date?\n{owner}: [[I'll send the {task} by {date}.]]",
            "{owner}: [[I'll send the {task} tomorrow.]]\n{other}: This transcript has no recorded date.",
        ],
        "multiple": [
            "{owner}: [[I'll send the {task}.]]\n{other}: [[I'll review the {second}.]]",
            "{other}: [[The {second} is mine to review.]]\n{owner}: [[The {task} is mine to send.]]",
            "{owner}: [[I will send the {task}.]]\n{other}: [[I will review the {second} by {date}.]]",
            "{owner}: [[Count on me for the {task}.]]\n{other}: I already sent my old notes. [[I'll review the {second}.]]",
            "{other}: [[I accept responsibility for reviewing the {second}.]]\n{owner}: [[I accept responsibility for sending the {task}.]]",
        ],
        "correction": [
            "{owner}: Can you send the {task}, {other}?\n{other}: [[Yes, I will send the {task}.]]",
            "{owner}: I cannot take the {task}.\n{other}: [[I'll send the {task} instead.]]",
            "{owner}: Who is sending the {task}?\n{other}: [[I'm taking responsibility for the {task}.]]",
            "{owner}: Don't list me as the sender of the {task}.\n{other}: [[Put my name down to send the {task}.]]",
            "{owner}: Is the {task} assigned to me?\n{other}: No. [[I'm the one who will send the {task}.]]",
        ],
    }


def make_case(category, family_index, variant, template):
    split = ["train", "train", "validation", "test", "test"][family_index]
    # Domains and names are disjoint across splits, as are wording families.
    domains = {
        "train": [("Maya", "Jon", "audit memo", "budget table"), ("Nia", "Sam", "design brief", "risk register"),
                  ("Omar", "Lee", "consent summary", "expense sheet"), ("Rae", "Pia", "test plan", "meeting agenda")],
        "validation": [("Tess", "Ivan", "release checklist", "support rota"), ("Zoe", "Hugo", "research appendix", "lab schedule")],
        "test": [("Amina", "Bilal", "vendor packet", "incident digest"), ("Cleo", "Dario", "migration guide", "access matrix")],
    }
    owner, other, task, second = domains[split][variant]
    values = dict(owner=owner, other=other, task=task, second=second, date=f"2026-11-{12 + variant:02d}")
    marked = template.format(**values)
    import re
    spans = re.findall(r"\[\[(.*?)\]\]", marked, flags=re.S)
    text = marked.replace("[[", "").replace("]]", "")
    timestamp = "2026-10-25T09:00:00+05:00" if category == "deadline" and family_index in {1, 2} else None
    gold = []
    for evidence in spans:
        is_second = second in evidence
        who = other if is_second or category == "correction" else owner
        deadline = values["date"] if values["date"] in evidence else None
        if timestamp and "tomorrow" in evidence:
            deadline = "2026-10-26"
        if timestamp and "in 2 days" in evidence:
            deadline = "2026-10-27"
        condition = None
        if category == "conditional":
            condition = ["legal signs off", "the budget is approved", "access is restored",
                         "the launch is not cancelled", "the committee votes yes"][family_index]
        gold.append({"claim": f"{'review' if is_second else 'send'} the {second if is_second else task}",
                     "owner": None if category == "ambiguous_owner" else who,
                     "recipient": other if f"to {other}" in evidence else None,
                     "deadline": deadline, "conditionality": condition,
                     "certainty": "ambiguous" if category == "ambiguous_owner" else "suggested",
                     "evidence": evidence, "action": "Review this commitment",
                     "match_terms": (second if is_second else task).split()})
    return {"id": f"{split}-{category}-{family_index}-{variant}", "split": split,
            "family": f"{category}-{family_index}", "category": category, "synthetic": True,
            "text": text, "source_timestamp": timestamp, "gold": gold}


def prepare(output=DATA):
    output.mkdir(parents=True, exist_ok=True)
    splits = {name: [] for name in ("train", "validation", "test")}
    for category, templates in families().items():
        for index, template in enumerate(templates):
            for variant in range(4 if index < 2 else 2):
                case = make_case(category, index, variant, template)
                splits[case["split"]].append(case)
    legacy = HERE.parent / "eval/cases.jsonl"
    legacy_texts = {json.loads(line)["text"] for line in legacy.read_text(encoding="utf-8").splitlines()}
    seen = set()
    for split, cases in splits.items():
        for case in cases:
            assert case["text"] not in seen | legacy_texts, "Duplicate source or development contamination"
            seen.add(case["text"])
            assert all(item["evidence"] in case["text"] for item in case["gold"])
        (output / f"{split}.jsonl").write_text(
            "".join(json.dumps(case, ensure_ascii=False) + "\n" for case in cases), encoding="utf-8", newline="\n")
    manifest = {"schema_version": 1, "synthetic": True, "generator_sha256": digest(Path(__file__)),
                "legacy_development_sha256": digest(legacy),
                "split_policy": "Authored template families, people and task domains disjoint across splits; no random row splitting.",
                "limitations": ["Small authored synthetic starter corpus, not a real-world benchmark.",
                                "Task concepts and annotation policy are shared across splits.",
                                "No independent human annotation audit has been performed."],
                "splits": {name: {"count": len(cases), "sha256": digest(output / f"{name}.jsonl"),
                                  "categories": dict(Counter(c["category"] for c in cases)),
                                  "families": sorted({c["family"] for c in cases})} for name, cases in splits.items()}}
    write_json(output / "manifest.json", manifest)
    return manifest


if __name__ == "__main__":
    print(json.dumps(prepare(), indent=2))
