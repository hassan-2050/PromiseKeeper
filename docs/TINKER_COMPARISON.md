# Tinker comparison: measured results

On October 25, 2026, a real Tinker LoRA run improved commitment F1 on 40 authored synthetic held-out transcripts, while reducing recall, owner accuracy and date accuracy and increasing observed latency. **The checkpoint fails the production quality guard. Local Ollama remains the default.** These results do not establish real-world accuracy or contest eligibility.

The comparison uses hosted `Qwen/Qwen3-8B` before and after training, with identical prompts and test inputs. The original quantized Ollama [55-case development evaluation](EVALUATION.md) is preserved and is not the baseline below.

| After existing pipeline checks | Hosted baseline | Fine-tuned epoch 1 |
| --- | ---: | ---: |
| True positives / false positives / misses | 32 / 10 / 0 | 31 / 4 / 1 |
| Precision | 0.7619 | 0.8857 |
| Recall | 1.0000 | 0.9688 |
| F1 | 0.8649 | 0.9254 |
| Owner accuracy, all 32 gold commitments | 32/32 (100%) | 29/32 (90.63%) |
| Owner accuracy, 28 known owners | 28/28 (100%) | 27/28 (96.43%) |
| Date accuracy, all 32 gold commitments | 32/32 (100%) | 31/32 (96.88%) |
| Date accuracy, two known dates | 2/2 | 2/2 |
| Strict raw schema validity, 40 responses | 21/40 (52.5%) | 40/40 (100%) |
| Raw quote substring rate | 100% | 100% |
| Mean remote sample latency | 2.520 s | 7.339 s |
| Nearest-rank p95 sample latency | 2.285 s | 8.166 s |

Owner/date denominators include missed commitments and null fields. The date regression above includes a missed commitment; two known dates are far too few for a broad deadline claim. Latency includes network/server waiting and cold calls, after client/tokenizer setup; this is not a controlled serving-speed comparison. A long baseline outlier makes its mean exceed p95.

The primary scores apply the same existing defaults, literal-quote gate, lexical filter, date resolver and exact duplicate grouping to both models. Strict raw schema validity is separate: the baseline often omitted `action`, which the existing app defaults. Raw schema-only F1 was 0.5965 versus 0.9254; using that as the headline would overstate the improvement relative to the application pipeline.

## Training and provenance

The run used 80 train, 20 validation and 40 test transcripts, with names, task domains and wording families separated across splits. Six rank-32 LoRA epochs used learning rate 0.0002, batch size 8, seed 20261025 and assistant-only cross-entropy loss. There were 60 training batches and 112,578 training tokens. Epoch 1 won validation selection; later complete ties retained the earlier epoch. Held-out scores did not select the checkpoint.

Selected sampler: `tinker://bc4a232a-4cf4-50dc-ab4e-3135c7171c90:train:0/sampler_weights/epoch-1`. State checkpoints and sampler paths for all six epochs are preserved in [run.json](tinker/run-20261025/run.json). They were saved with seven-day TTLs; remote availability after expiry is not promised.

A scoring implementation error was discovered from validation during the run: version 1 discarded responses missing `action`, unlike the existing Ollama adapter. Version 2 applies the existing defaults to both models while still recording strict raw invalidity. All preserved responses were rescored, and validation selection remained epoch 1. No additional held-out inference was needed. Original source/metrics and the correction are preserved. This is a disclosed repair on a small authored experiment, not a preregistered external benchmark.

Matching is a one-to-one lexical proxy using task nouns and annotated evidence overlap. It does not check action entailment, and a literal quote does not prove a promise or its owner. Families within each split are correlated. No independent annotation audit or confidence interval is claimed.

## What the demo shows

The fixed six-line messy handoff contains completed work, a hypothetical, an implicit obligation, a conditional review and an unresolved owner. **Both models missed Cleo's migration-guide commitment.** Both found Dario's conditional access-matrix review and the unassigned incident digest. The fine-tuned output makes the security condition more specific but does not improve detection in this fixed example.

A separate illustrative held-out refusal shows a real false-positive reduction: the baseline proposed "Not this time. My answer is no." as a commitment; the checkpoint returned an empty list. This case was selected after evaluation as the first negative case with fewer tuned false positives. It belongs to the same test set and is not another benchmark. [Both outputs and the full comparison](tinker/run-20261025/comparison.md) remain available.

The [new demo](TINKER_DEMO.md) shows saved measured outputs followed by a fresh remote checkpoint import, exact evidence, simulated reviewer edits, approval, a draft and cloud privacy labels. It uses an isolated synthetic database and an explicit per-import consent checkbox. A research-only flag accepts exact frozen synthetic texts despite the failed quality gate; ordinary Tinker activation remains blocked.

## Costs and artifacts

Measured tokens multiplied by the recorded public rates estimate **$0.049534 for training, $0.013408 for recorded sampling, $0.062942 combined**. Refreshed provider session usage reports the same gross estimated total. This excludes storage and separate live UI preview calls. These estimates are not an invoice, verified credit debit or remaining balance. [Provider billing evidence](tinker/run-20261025/billing.json) preserves time buckets, token counts and rates with account identities removed; actual invoice cost is unknown. The user reported $10 in credits; no out-of-pocket spend was authorized.

Review the [standalone HTML report](tinker/run-20261025/comparison.html), [artifact manifest and reproduction instructions](tinker/run-20261025/README.md), [raw and per-case metrics](tinker/run-20261025/comparison.json), [training log](tinker/run-20261025/training.jsonl), [token usage](tinker/run-20261025/token-usage.json) and [full protocol](TINKER_EXPERIMENT.md). These are actual run artifacts. Credentials are excluded. The DEV addendum remains unpublished and the new video awaits YouTube upload.
