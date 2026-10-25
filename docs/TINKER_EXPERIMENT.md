# Tinker experiment: real training workflow

The production PromiseKeeper extractor remains local Ollama `qwen3:8b`. The optional experiment uses Tinker's hosted `Qwen/Qwen3-8B` baseline and a LoRA adapter trained from that same hosted model. These are different deployments; the old quantized Ollama development score is not the Tinker baseline.

**Completed October 25, 2026:** six real LoRA epochs; validation selected epoch 1. Held-out pipeline F1 increased from 0.8649 to 0.9254, while owner/date accuracy and observed latency regressed. The production activation guard rejects the checkpoint. See [all measured outcomes](TINKER_COMPARISON.md), the [reviewable run bundle](tinker/run-20261025/README.md) and [actual demo](TINKER_DEMO.md).

## Verified setup and free credits

On October 25, 2026, the installed SDK was `tinker==0.35.0`. The user reported $10 in credits and authorized using those credits for the best verified result. The key is configured in the ignored project-root `.env`. Authenticated API calls verified that `Qwen/Qwen3-8B` is trainable and sampleable. The provider credit balance remains separately unverified. See [the preflight artifact](tinker/preflight.json) and [access status](tinker/access.json).

Default transport requests initially stalled on this host. Standard HTTP/2 calls reached the same official API. The experiment uses a version-scoped HTTP/2 compatibility shim in `tinker_lab/transport.py`; it replaces the SDK's private pyqwest transport factory in this process because ServiceClient 0.35.0 exposes no public transport injection hook. It preserves endpoint/authentication behavior and fails closed on an unreviewed SDK version. The workaround is recorded in configuration and never changes Ollama networking.

The [official Hacktoberfest challenge hub](https://dev.to/challenges/hf26) lists free Tinker partner credits, redeemable through [My Hacktoberfest promos](https://hacktoberfest.com/my/promos). Claim that offer and verify its amount, expiry and remaining balance in the [Tinker billing console](https://tinker.thinkingmachines.ai/billing/). No paid funding is assumed or authorized. The $200 in `update.txt` is a prize target, not an experiment spending budget.

Authentication is local: use `tinker auth login`, or set `TINKER_API_KEY` in the process environment or ignored project-root `.env`. Never commit or paste the key into an article, artifact or chat. The experiment loads the root `.env`; the normal app configuration is unchanged. No automatic purchase or payment setup exists in this code.

Primary references: [Tinker quickstart](https://tinker-docs.thinkingmachines.ai/tinker/quickstart/), [model rates](https://tinker-docs.thinkingmachines.ai/tinker/models/), [ServiceClient](https://tinker-docs.thinkingmachines.ai/tinker/api-reference/serviceclient/), [training operations](https://tinker-docs.thinkingmachines.ai/tinker/api-reference/trainingclient/), [billing usage](https://tinker-docs.thinkingmachines.ai/tinker/api-reference/restclient/). Tinker supports LoRA SFT and RL. This workflow uses supervised cross-entropy with assistant-only token loss; it does not use RL or Gemma.

## Dataset and protocol

`backend/tinker_lab/prepare_data.py` authors 140 synthetic transcripts: 80 train, 20 validation and 40 test. Ten categories cover explicit promises, implicit commitments, conditional obligations, refusals, completed work, hypotheticals, ambiguous owners, deadlines, multiple commitments and speaker attribution. Fifty wording families are assigned to splits before inference. Names, task domains and wording families do not cross splits. Variants within each family are correlated, so 140 rows should not be interpreted as 140 independent linguistic patterns.

The original 55 examples in `backend/eval/cases.jsonl` remain development data. They are not used for training or independent held-out scoring. The generated manifest records split hashes and the original corpus hash. All inputs are authored synthetic examples; the CLI never reads the SQLite source store. No independent human annotation audit has been performed. This is a small starter experiment, not a claim of real-world accuracy.

The labels preserve conditional obligations and leave ambiguous owners null. Relative dates are resolved only with a source timestamp; unresolved timing remains null. Training answers use the current extraction schema and literal source spans. Known production limitation: the existing lexical filter treats the word **provided** as completed work, including “I'll send the audit memo provided the budget is approved.” These positive training labels are retained. The filter remains unchanged; raw and pipeline scores expose different effects.

The fixed protocol is:

1. Verify frozen data and a pinned tokenizer revision; fetch current rates and account capabilities.
2. Evaluate the hosted baseline on validation and held-out test data before training. Save every raw response, token count, stop reason and latency.
3. Train six epochs of rank-32 LoRA, learning rate 0.0002, seed 20261025, batch size 8. This configuration was set before baseline collection. Only train split examples receive gradients. Prompt tokens have zero loss weight.
4. Save optimizer/state and sampler checkpoints each epoch. Select an epoch using validation pipeline F1, then output validity, then owner accuracy. Earlier epoch wins a complete tie. Test scores never select a checkpoint.
5. Evaluate the selected checkpoint on the identical test set exactly once in that run. Generate the report even if tuning regresses. Preserve failures and partial logs; never turn missing cases into successful empty answers.
6. Run a separate, fixed synthetic demo transcript before and after training. It is not included in the test metrics. A baseline error or improvement is not guaranteed.

Do not revise prompts, labels, hyperparameters or scoring after observing this test set and continue calling it independent. Further development needs a newly authored held-out set. Keep results from unsuccessful experiments too. A new run directory is required; the CLI refuses to overwrite one.

## Run commands (PowerShell, repository root)

```powershell
uv venv .venv
uv pip install --python .venv/Scripts/python.exe -r backend/tinker_lab/requirements.txt
.venv/Scripts/tinker.exe auth login
Set-Location backend
../.venv/Scripts/python.exe -m tinker_lab.experiment prepare
../.venv/Scripts/python.exe -m tinker_lab.experiment preflight --output ../docs/tinker/preflight.json
../.venv/Scripts/python.exe -m tinker_lab.experiment plan --output ../docs/tinker/plan.json
# Only after access, redeemed credits and a user-chosen usage limit are confirmed:
# Replace YOUR_LIMIT with a numeric USD estimate limit, including credit usage.
../.venv/Scripts/python.exe -m tinker_lab.experiment run --run-dir tinker_lab/runs/first --max-estimated-usd YOUR_LIMIT
# finalize is for the disclosed scorer correction on the original run; it can
# rescore preserved validation responses without retraining or editing test data.
../.venv/Scripts/python.exe -m tinker_lab.experiment finalize --run-dir tinker_lab/runs/first
../.venv/Scripts/python.exe -m tinker_lab.experiment report --run-dir tinker_lab/runs/first
../.venv/Scripts/python.exe -m tinker_lab.experiment billing --run-dir tinker_lab/runs/first
../.venv/Scripts/python.exe -m pytest -q
```

The dataset is checked into source control. `prepare` regenerates it deterministically; review label changes before freezing a run. `plan` downloads only tokenizer assets and public prices; it makes no paid inference or training calls. Python does not need local PyTorch or local model weights for this workflow. The tokenizer chat template requires Jinja2, included in the optional requirements. The SDK remains outside the production backend requirements.

## Metrics and costs

Precision, recall and F1 count individual commitments with one-to-one matching, including extra and missed commitments. Matching requires the authored task nouns in the claim and overlap with its annotated source span. This lexical proxy tolerates some action paraphrases but does not verify claim entailment or action semantics. Review raw predictions as well as aggregates. Per-category counts and per-case accepted predictions are preserved.

Owner and deadline exact accuracy use all gold commitments as the denominator, so misses count as incorrect. Additional known-owner and known-date scores exclude null labels. Raw schema validity, truncation, literal-quote validity and filtered pipeline results are reported separately. The pipeline applies the existing adapter defaults, literal-quote gate, lexical filter, date resolver and exact duplicate grouping. Latency is timed around each remote sample call and includes remote waiting and initial slow calls; tokenizer/client setup is excluded. Mean and nearest-rank p95 are shown. Validation traffic is distinguished from test and demo traffic in token accounting.

Scoring version 1 incorrectly discarded an entire response when its `action` field was missing, even though the production Ollama adapter supplies a default. This was discovered from a validation response during the first run, after baseline collection. Version 2 applies the existing defaults to both models before pipeline validation while still counting the omission against strict raw schema validity. `finalize` rescores saved outputs and reselects the checkpoint on validation only. Original logs and checkpoint choices remain preserved. If selection changes, the earlier final outputs remain and the corrected selection uses distinct filenames. This is a disclosed scoring implementation repair, not a preregistered external benchmark.

The [local token plan](tinker/plan.json) estimates about $0.19 at its recorded public rates for 60 training batches and 222 sampling requests, assuming every response reaches the maximum token count. Its buffered estimate is about $1.24, including a 25% token buffer and $1 storage reserve. **These are estimates, not actual charges or a provider-enforced cap.** Rates, retries, storage and credits may change the amount due. The script refuses a buffered estimate above the supplied limit; provider billing controls remain necessary for a hard account spending cap.

Runs preserve measured token usage, rate-card estimates and, where accessible, session-filtered provider billing events. Provider `estimated_cost_usd` means gross estimated usage before credits/commits; it is not an invoice amount. Usage can lag hours. Refresh it later with `billing`; org-wide unrelated usage is not attributed to this run. Unattributed storage is excluded and marked unknown, not free. Checkpoints expire after seven days by default; download or explicitly retain needed artifacts before expiry, accounting for storage charges. Actual invoice cost remains null until verified separately.

The completed run recorded 112,578 training tokens: $0.049534 at the captured rate. Recorded sampling adds $0.013408, for $0.062942 combined. The refreshed provider session events report the same gross estimate. Storage and separate UI preview requests are outside that total. The public bundle removes billing user names/identifiers but preserves session, model, token counts, rates, costs and time buckets. The original unredacted snapshot remains only in the ignored local run.

## Artifacts and integration boundary

Each local ignored run directory contains frozen train/validation/test JSONL, the dataset manifest inside `plan.json`, configuration/rates, exact Python environment, Git revision and source snapshots/hashes, raw baseline and epoch validation outputs, raw final outputs, per-step loss/timing/tokens, state/sampler checkpoint identifiers, the selection decision, provider usage, token usage, and Markdown/HTML comparisons. The report generator refuses incomplete runs or changed frozen data. Review/redact billing and account details before explicitly selecting artifacts for publication.

`tinker_lab/adapter.py` samples and validates output against the shared contract. The default `/api/import` path remains Ollama. The optional `EXTRACTION_PROVIDER=tinker` flag also requires `TINKER_VERIFIED_RUN` to point at a finalized run. Its guard verifies corpus hashes, checkpoint identity, complete non-truncated JSON outputs, and no held-out regression in pipeline F1, owner accuracy or date accuracy. Every remote import needs `allow_remote_inference=true`; the UI shows cloud processing and requires a checkbox for each source. The literal-quote and human-approval checks remain at the API layer. A checkpoint cannot be activated while its run is incomplete.

This checkpoint is technically compatible with the shared contract but fails that quality gate: owner accuracy fell from 32/32 to 29/32 and all-gold date accuracy from 32/32 to 31/32. **Ordinary Tinker activation is blocked.** For the recorded experiment only, `TINKER_SYNTHETIC_PREVIEW=true` bypasses the quality threshold while retaining provenance checks, explicit consent and an exact-text allowlist of the frozen synthetic train/validation/test/demo inputs. Any unseen source is rejected before a remote call, with no persisted source. This research setting is displayed in the import UI and is not suitable for general notes.

A saved Tinker sampler path requires remote inference; an Ollama replacement would require export and adapter/weight-format compatibility tests that have not run. The pinned Hugging Face tokenizer identifies client tokenization, not a separately verified server weight digest. No direct LoRA-to-Ollama compatibility is claimed.

The optional backend dependencies are required in the API environment. Launch a separate demo API process with the flag and an absolute run path, loading its key with `uvicorn --env-file ../.env`. Do not change the default provider until the checkpoint passes the guard and live verification. Remote mode discloses that source text leaves the machine and that deleting the local source does not delete provider-side records. Local mode retains its original on-device labels and behavior.

`demo/record_tinker_demo.mjs --run-dir PATH` captures actual results, a real remote import after consent, evidence review, approval, a draft and privacy controls. It fails unless the live API uses the exact finalized checkpoint. It writes separate screenshots and video under `demo/assets/tinker`, preserving the original demo. The narration renderer accepts `--sections`, `--assets-dir` and `--cache-dir` to render the new recording with the existing user-selected `af_sarah` voice without replacing old media.

Both baseline and tuned outputs missed Cleo's implicit migration-guide obligation in the fixed messy demo. The report also shows the first negative held-out example with fewer tuned false positives: a soft refusal. That illustration was selected after evaluation, disclosed as such, and does not create a new benchmark or change checkpoint selection. The UI import is a fresh request to the checkpoint, not a replay; report comparisons display preserved actual API outputs. The sampler is warmed with a separate frozen negative training example before video capture, and scene holds support narration. Neither the recording nor its edited runtime is a latency benchmark.

## Publication status

The available-credit ceiling is $10; no out-of-pocket spending is authorized. Measured outcomes and verification status are [recorded separately](TINKER_COMPARISON.md). The [new Tinker demo is on YouTube](https://www.youtube.com/watch?v=5HudDBuLpbU). The existing local-model demo and its real YouTube URL are preserved. The [DEV article](https://dev.to/hassan_shah_733ea1eb37c88/i-built-an-ai-that-remembers-the-promises-we-forget-9db) includes the Tinker experiment; its live content is [verified](PUBLICATION_VERIFICATION.md). [The editable article source](DEV_TINKER_ADDENDUM_DRAFT.md) remains available locally. The user selected `hassan-2050/PromiseKeeper` for GitHub updates; obtain approval before further authenticated DEV edits.
