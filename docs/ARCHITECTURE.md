# Architecture

```mermaid
flowchart LR
  U[Browser UI] -->|local HTTP| A[FastAPI]
  A -->|JSON prompt / structured output| O[Ollama]
  O --> Q[Qwen3 8B · local]
  A -->|validated source + suggestions| D[(SQLite)]
  A -->|quotes checked against original text| A
```

The Next.js client manages import, review, approval and drafts. FastAPI coordinates local Ollama inference and persists source documents, commitments and drafts in SQLite. Model-proposed quote strings are accepted only if they are literal substrings of the supplied source. The UI labels AI suggestions and requires explicit human approval before a follow-up can be drafted. Draft content is never sent.

The initial schema stores `SourceDocument`, paragraph-level `SourceFragment` records with source character offsets, `Commitment`, multiple `Evidence` quotes per grouped exact duplicate, `Draft`, and `AuditEvent` rows for reviewer edits and status decisions. P1 work should add people/project entities, asynchronous processing jobs, sentence-embedding duplicate candidates, and richer timeline views.
