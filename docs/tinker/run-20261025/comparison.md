# PromiseKeeper: measured Tinker comparison

Authored synthetic held-out set. These results do not establish real-world accuracy or contest eligibility.

Base model: `Qwen/Qwen3-8B`. Checkpoint: `tinker://bc4a232a-4cf4-50dc-ab4e-3135c7171c90:train:0/sampler_weights/epoch-1`.
Test SHA-256: `bea268ceda52ebe2a196020ce174770d7bdcf816c704f62efb1ef90a0050c31c`.

Scoring correction: Version 2 applies existing Ollama action/certainty defaults before pipeline validation, without changing strict raw schema validity. Corrected both models and reselected on validation only.

## After existing evidence, date and duplicate checks

| Metric | Baseline | Fine-tuned |
| --- | ---: | ---: |
| Precision | 0.7619 | 0.8857 |
| Recall | 1.0000 | 0.9688 |
| F1 | 0.8649 | 0.9254 |
| Owner accuracy (all gold commitments) | 1.0000 | 0.9062 |
| Owner accuracy (known owners) | 1.0000 | 0.9643 |
| Date accuracy (all gold commitments) | 1.0000 | 0.9688 |
| Date accuracy (known dates) | 1.0000 | 1.0000 |
| Output validity | 0.5250 | 1.0000 |
| Raw quote substring rate | 1.0000 | 1.0000 |
| Mean latency, seconds | 2.5201 | 7.3393 |
| P95 latency, seconds | 2.2854 | 8.1663 |

TP / FP / FN: baseline 32 / 10 / 0; fine-tuned 31 / 4 / 1.

Gold commitments: 32; known-owner denominator: 28; known-date denominator: 2.

## Raw model output

| Metric | Baseline | Fine-tuned |
| --- | ---: | ---: |
| Precision | 0.6800 | 0.8857 |
| Recall | 0.5312 | 0.9688 |
| F1 | 0.5965 | 0.9254 |
| Owner accuracy (all gold commitments) | 0.5312 | 0.9062 |
| Owner accuracy (known owners) | 0.4643 | 0.9643 |
| Date accuracy (all gold commitments) | 0.5312 | 0.9688 |
| Date accuracy (known dates) | 0.0000 | 1.0000 |
| Output validity | 0.5250 | 1.0000 |
| Raw quote substring rate | 1.0000 | 1.0000 |
| Mean latency, seconds | 2.5201 | 7.3393 |
| P95 latency, seconds | 2.2854 | 8.1663 |

TP / FP / FN: baseline 17 / 8 / 15; fine-tuned 31 / 4 / 1.

Gold commitments: 32; known-owner denominator: 28; known-date denominator: 2.

## Costs

Measured token counts and rate-card estimates are in `token-usage.json`. Provider-reported session usage is in `billing.json` when available. Gross usage estimates, credits used and invoice amount due are different quantities. Actual invoice cost: **unavailable** until independently verified. Storage and unassigned billing events are not assumed to be free.

Training tokens: 112578; training rate-card estimate: $0.049534.

All recorded sampling rate-card estimate: $0.013408; training plus recorded sampling: $0.062942. Storage and separate live UI preview requests are outside this token total.

Provider session usage snapshot (2026-10-25T12:38:40.548810+00:00) reports $0.062942 gross estimated usage. This is not an invoice or verified credit debit.

## Scoring limits

One-to-one task-noun and annotated-evidence overlap matching is a lexical proxy. It does not prove semantic entailment. Owner/date denominators include missed gold commitments and unresolved null fields; known-only scores are also shown. Malformed/truncated JSON cannot earn true positives. Strict raw schema validity is separate from pipeline scoring: the latter supplies the existing adapter's default action text and certainty before validating individual candidates. Latency measures each remote sample call, including server waiting, after client/tokenizer setup. Check the raw outputs, errors and per-category counts before interpreting any change.

## Fixed synthetic demo

```text
Synthetic handoff, noisy meeting notes
Amina: I sent last month's vendor packet already.
Bilal: A new packet could be useful, but I haven't agreed to one.
Cleo: Leave the migration guide with me.
Dario: If security signs off, I'll review the access matrix by 2026-11-18.
Amina: Someone still needs to send the incident digest. Owner undecided.
```

### Baseline

```text
{
  "commitments": [
    {
      "claim": "review the access matrix by 2026-11-18",
      "owner": "Dario",
      "recipient": null,
      "deadline": "2026-11-18",
      "conditionality": "conditional",
      "certainty": "suggested",
      "evidence": "If security signs off, I'll review the access matrix by 2026-11-18."
    },
    {
      "claim": "send the incident digest",
      "owner": null,
      "recipient": null,
      "deadline": null,
      "conditionality": "unconditional",
      "certainty": "ambiguous",
      "evidence": "Someone still needs to send the incident digest. Owner undecided."
    }
  ]
}
```

### Finetuned

```text
{"commitments": [{"claim": "review the access matrix", "owner": "Dario", "recipient": null, "deadline": "2026-11-18", "conditionality": "security signs off", "certainty": "suggested", "evidence": "If security signs off, I'll review the access matrix by 2026-11-18.", "action": "Review this commitment"}, {"claim": "send the incident digest", "owner": null, "recipient": null, "deadline": null, "conditionality": null, "certainty": "ambiguous", "evidence": "Someone still needs to send the incident digest. Owner undecided.", "action": "Review this commitment"}]}
```

## Illustrative held-out case

Selected after evaluation to illustrate one reduction in false positives. This is part of the same test set, not an additional benchmark. The full results include regressions.

Case: `test-refusal-4-0`.

```text
Bilal: Can we count on you for the vendor packet?
Amina: Not this time. My answer is no.
```

### Baseline actual test output

```text
{
  "commitments": [
    {
      "claim": "Not this time. My answer is no.",
      "owner": null,
      "recipient": null,
      "deadline": null,
      "conditionality": null,
      "certainty": "ambiguous",
      "evidence": "Not this time. My answer is no.",
      "action": "proposed next action"
    }
  ]
}
```

### Finetuned actual test output

```text
{"commitments": []}
```

The fixed synthetic demo was authored before inference. Its raw outputs are separate from the post-evaluation illustrative case. Screenshots and recordings of the live review interface have their own capture provenance; this report alone does not verify that journey.
