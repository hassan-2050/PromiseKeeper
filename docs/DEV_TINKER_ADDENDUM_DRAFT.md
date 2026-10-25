---
title: "PromiseKeeper: fewer false promises with a real Tinker fine-tune"
published: false
tags: devchallenge, hf26challenge, opensource, ai
---

*This is a submission for the [Hacktoberfest Open-Source AI Challenge Week 3: Slow and Steady](https://dev.to/challenges/hacktoberfest-week3-2026-10-19)*

<!-- Unpublished revision draft for review. The existing published article is unchanged. DEV publication requires approval. -->

## What I Built

A promise can disappear inside a paragraph of meeting notes. Before following up, someone has to find the conversation, work out who offered to do what, and check whether the date was actually agreed.

I built PromiseKeeper to turn that rereading into a review queue. Import pasted notes or a `.txt`/`.md` file, and an open-weight language model proposes commitments beside their exact source quotes. A person can correct the owner, keep a condition visible, approve a real obligation, or dismiss a suggestion. Approved items appear in a timeline and can become editable follow-up drafts. Nothing is sent automatically.

The intended payoff is less hunting through conversations for researchers, project coordinators and anyone who keeps track of informal agreements. The app does the first pass; the person makes the decision. I have not measured real-world time saved. The demos and evaluation use explicitly synthetic notes.

The existing application uses local Qwen3 8B through Ollama, with Next.js, FastAPI and SQLite. For this update, I ran a real Tinker fine-tuning experiment to test whether task-specific training could reduce false promises. It improved precision and F1 on a small held-out synthetic set, but owner accuracy and observed latency regressed. Local Ollama therefore remains the default.

## Demo

{% youtube 5HudDBuLpbU %}

[Watch the updated Tinker experiment demo](https://www.youtube.com/watch?v=5HudDBuLpbU). The 140-second recording shows the measured comparison, a fresh checkpoint request, evidence review, approval, an editable follow-up and the cloud privacy boundary.

![Actual checkpoint suggestions awaiting review](https://raw.githubusercontent.com/hassan-2050/PromiseKeeper/00aa639f0a793d533e64d427a07ccf2f26891e1c/demo/assets/tinker/screenshots/checkpoint-evidence-review.png)

The recording uses a separate research preview restricted to exact frozen synthetic examples, with explicit cloud consent for each import. A simulated reviewer keeps the security sign-off condition visible before approving Dario's access-matrix review. The sampler connection was warmed before recording, and scene holds support natural narration; the video is not a latency benchmark. Deleting a local source does not delete provider-side records.

## Code

[Browse PromiseKeeper on GitHub](https://github.com/hassan-2050/PromiseKeeper).

The repository includes the application, deterministic dataset preparation, training workflow, regression tests, actual screenshots and recording scripts. The [experiment bundle](https://github.com/hassan-2050/PromiseKeeper/tree/main/docs/tinker/run-20261025) preserves frozen data, raw outputs, per-case scores, all six checkpoint identifiers, training logs, costs, and source/environment snapshots. The [full comparison](https://github.com/hassan-2050/PromiseKeeper/blob/main/docs/TINKER_COMPARISON.md) and [demo verification](https://github.com/hassan-2050/PromiseKeeper/blob/main/docs/TINKER_DEMO.md) explain the evidence and limitations.

Twenty backend tests pass, including evidence validation, approval boundaries, scorer parity and the synthetic preview restriction. The production frontend build, a real local-model browser journey and scoped automated accessibility checks also passed.

## How I Built It

The default path sends an extraction prompt to local Ollama, validates the response with Pydantic and independently rejects evidence that is not a literal substring of the source. SQLite stores sources, suggestions, reviewer edits and drafts. Human approval is required before drafting a follow-up. The Tinker adapter shares that extraction contract; it does not replace the application.

### A real Tinker experiment

The data contains 80 training, 20 validation and 40 held-out authored synthetic conversations. It covers explicit promises, implicit responsibility, conditions, refusals, completed work, hypotheticals, unresolved owners, deadlines, multiple commitments and speaker attribution. Wording families, names and task domains are separated across splits. The app's previous 55-case development corpus was preserved and was not reused as this experiment's independent benchmark.

The baseline and fine-tuned model both use hosted `Qwen/Qwen3-8B`, the same prompt and the same held-out inputs. This avoids treating a previous quantized Ollama score as an equivalent cloud baseline. All baseline outputs were collected before training.

Tinker ran six epochs of rank-32 LoRA supervised fine-tuning with assistant-only loss, learning rate 0.0002, batch size eight and seed 20261025. The run recorded 60 batches and 112,578 training tokens. State and sampler checkpoints were saved each epoch. Validation selected epoch one, with earlier epochs winning complete ties. Test scores did not choose a checkpoint.


The workflow uses `tinker==0.35.0` with a pinned tokenizer revision. Default SDK transport stalled on this host; a documented, version-scoped HTTP/2 compatibility shim allowed authenticated requests to the same official API. That workaround is confined to the experimental path.

### Measured results

The primary results include the application's existing defaults, evidence checks, date resolution and exact duplicate grouping:

| Metric on 40 held-out synthetic transcripts | Baseline | Fine-tuned |
| --- | ---: | ---: |
| True positives / false positives / misses | 32 / 10 / 0 | 31 / 4 / 1 |
| Precision | 0.7619 | 0.8857 |
| Recall | 1.0000 | 0.9688 |
| F1 | 0.8649 | 0.9254 |
| Owner accuracy, all 32 gold commitments | 100% | 90.63% |
| Date accuracy, all 32 gold commitments | 100% | 96.88% |
| Strict raw schema validity | 52.5% | 100% |
| Mean observed sample latency | 2.520 s | 7.339 s |

Known-date accuracy remained two out of two for both models. That denominator is too small for a general deadline claim. The date score above also counts null fields and misses. Latency includes remote waiting and network effects; it is not a controlled hardware benchmark.

![Actual measured comparison](https://raw.githubusercontent.com/hassan-2050/PromiseKeeper/00aa639f0a793d533e64d427a07ccf2f26891e1c/demo/assets/tinker/screenshots/measured-comparison.png)

One illustrative refusal exposes a useful improvement. Asked about a vendor packet, Amina replies: "Not this time. My answer is no." The baseline extracted that refusal as a possible commitment. The checkpoint returned `{"commitments": []}`. This example was selected after evaluation to illustrate fewer false positives; it is part of the same test set, not another benchmark.

The fixed messy handoff is less flattering. Both models missed "Leave the migration guide with me." Both extracted a conditional security review and an unassigned digest. The fine-tuned condition was more specific, but detection did not improve in that example. The report preserves both outputs.


### Limits and the production decision

A scorer error surfaced in validation during the run: version one discarded an entire response if `action` was missing, while the existing Ollama adapter supplies a default. I repaired that parity issue for both models, preserved strict raw validity as a separate metric, and rescored saved responses. Validation still selected epoch one, without another held-out inference pass. The original code, outputs and correction remain available.

The matcher uses task nouns and evidence overlap, not full semantic entailment. These are small, correlated, synthetic families without an independent annotation audit. The existing lexical filter also mishandles conditional "provided"; the difficult positive examples remain in training rather than being removed to improve a score. Literal evidence proves where a suggestion came from, not that its interpretation is correct.


The checkpoint is technically compatible with the shared extraction contract, but its owner/date regressions fail the production quality guard. Ordinary Tinker activation is blocked. The separate synthetic-only preview demonstrates the actual saved checkpoint while preserving consent, literal-quote checks and approval. Further tuning needs fresh held-out data.

Measured tokens at recorded public rates estimate $0.049534 for training and $0.013408 for recorded sampling: about $0.063 combined, excluding storage and separate live preview calls. The provider's session usage later reported the same gross estimate. That is not an invoice or verified credit deduction. Actual invoice cost remains unknown.

## Why Does Open Innovation Matter?

Open weights let me choose where the model runs and adapt it to the task. The default Qwen model runs on my machine through Ollama, so source conversations stay with the local service. Tinker let me train and evaluate a LoRA adapter from the same hosted open-weight baseline, preserve the checkpoint identifiers, and inspect the failures alongside the gains.

The source code also makes the decision boundary inspectable: a quote must match the source, uncertainty stays visible, and an AI suggestion cannot send a message. Others can change those rules, reproduce the synthetic evaluation, or try another model. A closed model API could produce structured suggestions, but would not provide the same control over local weights and task-specific adapters.

The remote Tinker checkpoint is not an Ollama-ready export; that compatibility has not been established. Open weights do not make the cloud experiment private or cost-free. The demo narration uses the open-weight Kokoro-82M model with the user-selected `af_sarah` voice, with model and voice hashes recorded.

## Prize Categories

I am entering **Best Use of Tinker**. I used Thinking Machines' Tinker to fine-tune Qwen3-8B for commitment extraction and compared it with the same hosted baseline. Held-out synthetic-test precision improved from 0.7619 to 0.8857 and F1 from 0.8649 to 0.9254. The report includes recall, owner/date and latency regressions; these measurements are not a guarantee of real-world accuracy or judging eligibility.
