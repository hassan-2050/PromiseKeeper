Title: I Built an AI That Remembers the Promises We Forget

Tags: `devchallenge`, `hf26challenge`, `opensource`, `ai`

---

*This is a submission for the [Hacktoberfest Open-Source AI Challenge Week 3: Slow and Steady](https://dev.to/challenges/hacktoberfest-week3-2026-10-19)*

## What I Built

The report was supposed to arrive yesterday. Somewhere in last week's notes, someone said they would send it. Before asking for an update, a researcher has to reconstruct the conversation: who offered, what they offered, and whether there was actually a deadline.

That is the fictional situation in my explicitly synthetic demo. It captures a familiar kind of work: remembering the small agreements that never became formal tasks.

I built PromiseKeeper to turn those agreements into a queue a person can check. Import meeting notes, a chat transcript, or a text file. A local language model proposes commitments. Every suggestion stays beside the exact words that support it. The reviewer can approve it, correct it, dismiss it, or mark it complete.

An approved promise can then become a polite follow-up draft. The person reviews and edits the wording, and decides whether to send it. PromiseKeeper has no sending integration.

The app is built around the difference between a possible promise and a confirmed one. “I'll send the report” deserves attention. “I already sent the report” describes something finished. “If the samples clear, I'll upload the appendix” carries a condition that should stay attached. An uncertain date should remain uncertain.

The interface gives those distinctions room: an evidence review inbox, upcoming and overdue summaries, a timeline, follow-up drafts, and local privacy controls. It supports pasted text and `.txt` or `.md` files. SQLite stores the sources and review decisions on the same machine as the local model.

The desired payoff is modest and concrete: bring the relevant promise back into view, with enough context to decide the next step.

I designed the workspace around reading and deciding: a left sidebar, vertically arranged input fields, and charcoal, forest-green and mint surfaces. Source quotes stay readable inside each card. The mobile drawer supports keyboard focus and Escape, and the help dialog explains the review boundary. Follow-up drafts can be copied or downloaded; source deletion lets the person check exactly what they are removing.

## Demo

{% youtube rhyfJHkMmrs %}

[Watch the demo on YouTube](https://www.youtube.com/watch?v=rhyfJHkMmrs). The redesigned interface is demonstrated in a 112.36-second, 1920x1080 recording narrated by genuine Kokoro-82M using `af_sarah`. The local export is saved at `demo/assets/video/final_demo.mp4`.

The recording follows a researcher importing five snippets of synthetic notes. Actual local Qwen inference finds three candidates: a revised field report, cleaned survey figures, and a conditional appendix. The already-delivered consent forms and vague conference thought stay out of the action queue.

![Synthetic research notes in the actual import screen](https://raw.githubusercontent.com/hassan-2050/PromiseKeeper/ca7f7f1b4ee8bb53049e8db88cf647e37728fe10/demo/assets/screenshots/input-notes.png)

The reviewer checks the quotes, approves the report, and sees one confirmed promise past its date. Two suggestions remain available for review.

![Exact source quotes beside the extracted suggestions](https://raw.githubusercontent.com/hassan-2050/PromiseKeeper/ca7f7f1b4ee8bb53049e8db88cf647e37728fe10/demo/assets/screenshots/evidence-review.png)

![Dashboard after approving the overdue report](https://raw.githubusercontent.com/hassan-2050/PromiseKeeper/ca7f7f1b4ee8bb53049e8db88cf647e37728fe10/demo/assets/screenshots/overdue-dashboard.png)

The final action is preparing an editable follow-up. The draft asks whether the recorded timing has shifted; it does not assume the person has failed to deliver.

![An editable follow-up draft that the user must review](https://raw.githubusercontent.com/hassan-2050/PromiseKeeper/ca7f7f1b4ee8bb53049e8db88cf647e37728fe10/demo/assets/screenshots/reviewed-follow-up.png)

![Local model status, export and data deletion controls](https://raw.githubusercontent.com/hassan-2050/PromiseKeeper/ca7f7f1b4ee8bb53049e8db88cf647e37728fe10/demo/assets/screenshots/privacy-controls.png)

These are screenshots of the working application. The video preserves the browser's original action timing, with added scene holds for narration. Its edited runtime is not a processing benchmark.

## Code

[Browse PromiseKeeper on GitHub](https://github.com/hassan-2050/PromiseKeeper). The repository includes the frontend, backend, synthetic evaluation corpus, API tests, browser smoke test, real application screenshots, and recording and narration scripts. The recording and narration scripts reproduce the demo; generated video and WAV files are local outputs.

The code is MIT licensed. The selected Qwen model and Kokoro weights have their own licenses and are downloaded separately.

The manual setup uses Python 3.12+, Node 22+, and Ollama. Pull `qwen3:8b`, start the FastAPI service on port 9000, and run the Next.js frontend. The README contains the commands and a Docker Compose option. There is no paid inference service to configure.

Useful places to begin reading are `backend/app/main.py` for the extraction and review boundary, `app/page.tsx` for the user journey, and `backend/eval/run_evaluation.py` for the measured synthetic evaluation. `demo/record_demo.ts` and `demo/narrate_demo.py` reproduce the screen recording and voiceover.

## How I Built It

The frontend uses Next.js and TypeScript. FastAPI handles import, local inference, validation, review updates, drafting, export and source deletion. SQLAlchemy stores the relationships in SQLite.

The processing path is small enough to inspect:

```text
Notes → source document and paragraph fragments
      → local Ollama / Qwen extraction
      → schema validation and source-quote check
      → evidence-linked suggestions in SQLite
      → human review → approved promise → editable draft
```

The configured extractor is Qwen3 8B through Ollama. The locally inspected model reports 8.2 billion parameters and Q4_K_M quantization. The evaluation records the model digest, rather than relying only on a tag that could later point to different weights. Structured extraction runs at temperature zero with reasoning disabled.

The model proposes an action, owner, recipient, deadline, condition, certainty, evidence quote and next step. Pydantic checks the shape of those values. The API then independently verifies that each evidence quote is a literal substring of the original source text. A plausible quote that does not occur in the notes is rejected.

That boundary is useful, but deliberately limited. A quote can be present and still fail to support the proposed owner or claim. The source check establishes provenance; the reviewer still has to establish meaning. The interface keeps the quote beside the action so that check can happen where the decision is made.

The backend also applies conservative lexical rejection to obvious refusals, completed actions and hypothetical statements. An earlier development run exposed false positives in these cases. The final measurements therefore describe the combined prompt, model, schema checks and filters. They are not a score for the base model alone.

Dates need a similar distinction. Explicit dates can be stored directly. Relative timing can be interpreted only when a source timestamp is known. Without that anchor, the date stays unresolved. A missing owner is allowed to remain missing too; filling a field with a confident guess would make the queue less trustworthy.

Each source is split into paragraph fragments with character offsets. Evidence records preserve quotes and their locations. When the same extraction key repeats within an import, the API groups it while retaining distinct supporting quotes. This is normalized exact grouping, not semantic deduplication. Two differently phrased obligations can remain separate, and exact grouping has its own limits when conditions differ. Broader similarity matching needs more work before it should alter a person's action queue.

Review changes create audit events. A source deletion removes its linked commitments and drafts. The dashboard counts confirmed overdue items, and CSV export includes approved commitments with their evidence. The prototype is intended for a person's local machine; shared hosting, account permissions and encrypted storage are separate deployment concerns.

Follow-up drafting uses a deterministic template assembled from approved fields. It does not ask a second model to invent background context, recipients, or excuses. The local model's core job is finding candidate obligations in unstructured conversation. Once the person approves the fields, predictable drafting keeps the next step inspectable.

I checked the implementation with four backend API tests and a production build including TypeScript checks. The browser journey uses genuine local Qwen inference and covers file loading, quote inspection, owner/date/note edits, approval, editable draft copy and download, the timeline, CSV export, completion, source deletion and cancellation, help, mobile keyboard navigation and dark mode. A later import is checked to ensure it does not inherit the previous source timestamp. Automated axe checks report zero violations for the selected rules across 16 light/dark page, dialog and mobile-drawer states; that is a scoped automated check, not a complete manual accessibility audit. The recording runs the actual browser, backend and local model.

For extraction, I authored 55 labelled synthetic cases across 11 categories. The preserved run produced these results:

| Check | Measured result |
| --- | --- |
| Case-level commitment classification | 40 true positives, 0 false positives, 0 false negatives |
| Owner exact match | 30 of 35 eligible cases |
| Explicit calendar-date exact match | 5 of 5 eligible cases |
| Accepted quote substring check | 41 of 41 accepted candidate quotes |

The owner result is the most useful warning in that table: the system can identify a possible obligation and still attribute it incorrectly. In this corpus, implicit-owner examples account for the five owner mismatches.

The perfect classification result is a small development-set observation. These cases are authored, repetitive, and were used while improving the pipeline. Quote validity is also an enforced acceptance rule, so its perfect rate is not independent evidence of understanding. The evaluation does not score claim entailment and does not cover sarcasm, multilingual conversations, noisy transcription, contradictions, or the full range of date language. The five date examples are a narrow check.

The corpus, evaluator and per-case outputs are preserved so a reader can inspect those limits and add harder examples. Real conversations and a held-out evaluation would be the next useful evidence.

## Why Does Open Innovation Matter?

A commitment assistant handles information that can be mundane in isolation and sensitive in combination: who is waiting for whom, which deadline is slipping, and what people agreed to in a private discussion.

Running an open-weight extractor locally makes the data path understandable. After the model has been downloaded, inference does not need a hosted model account. The notes go from the local app to the configured local Ollama service, and the resulting records stay in SQLite. The demo uses synthetic material, but the architecture is chosen for conversations a person would want to keep private.

Open components also make failure inspectable. I can retain a failing synthetic example, adjust the prompt or acceptance filter, and run the same evaluator again. A model digest, a source quote, and a saved result give someone else something concrete to investigate. They can replace the model adapter and keep the validation and human review boundaries.

There are costs to that choice. An eight-billion-parameter model needs a substantial download and enough memory. Local inference can be slow or unavailable on a particular computer. Initial setup is more work than entering a hosted API key. The UI exposes model availability and processing failures because those constraints affect the user's experience.

The same approach carries into the video. Kokoro runs locally, its selected voice and weight hashes are recorded, and the narration script and caption timings are included. The demonstration can be regenerated from the project instead of depending on an unexplained media asset.

## The Lazy Payoff

The visible transformation is five raw snippets becoming three candidate obligations, then one approved overdue report and an editable follow-up. The person makes the important decisions while the app gathers the relevant words into one place.

I have not measured saved hours, fewer missed deadlines, or reduced stress. The synthetic demonstration shows a workflow, and the evaluation measures a narrow extraction task. Neither establishes a productivity improvement for real teams.

The burden I want to reduce is repeatedly reconstructing the same agreement before taking a small, reasonable next step. Sometimes that step is sending a reminder. Sometimes it is noticing a condition and waiting. Sometimes it is rejecting the suggestion because there never was a promise.

Keeping that choice with the person matters as much as finding the sentence. A useful assistant should help us remember what we owe one another, while leaving room for people to explain what changed.

## Prize Categories

Overall **Slow and Steady** challenge entry.
