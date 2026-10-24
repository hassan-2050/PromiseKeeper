# Workspace redesign

The revised interface follows the user's constraints: a left sidebar, vertically stacked forms, charcoal and forest green with mint accents, and direct actions. It does not use top navigation tabs, horizontal form choices, a blue/amber palette, or wizard/stepper controls.

## What changed

- A readable overview with actual review, confirmed, past-due and unresolved-owner counts, priority commitments and upcoming dates.
- Evidence cards with the original quote, owner, conditionality, source name and expandable paragraph/character location. Review fields remain editable.
- A mobile drawer with keyboard focus containment, Escape dismissal and focus restoration. The help button now opens a working native dialog.
- A single vertical import form. Loading a text file fills the editor for review; inference starts only when the person clicks Find the promises. A successful import clears its source timestamp so a later conversation cannot accidentally inherit that date.
- A date-grouped timeline for confirmed promises. Unresolved dates have their own group; only valid calendar dates contribute to past-due counts.
- A follow-up editor with working clipboard and text download actions. Drafts still use approved fields and require the user to send them.
- Privacy controls that allow reviewing and deleting an individual source and its linked records, with an explicit keep/delete choice.
- Feedback for network/action errors, busy actions, saved edits and completed imports. Light and system dark themes use the same interface.

The backend extraction and measured 55-case evaluation are unchanged. The evaluation figures refer to the preserved run in `docs/eval_run.json`; they are not newly measured real-world accuracy.

## Verification

- `npm run build`: successful production build, including TypeScript checks.
- Backend API tests: 4 passed.
- `npm run test:e2e`: passed against the production server and real local Qwen inference. Covers file loading, extraction, original evidence, edit validation, approval, editable draft copy/download, dated timeline, CSV export, completion, source deletion/cancellation, help, mobile navigation/focus, date reset and dark mode.
- `npm run test:a11y`: 16 light/dark page, dialog and mobile navigation states with zero reported violations for the selected automated WCAG 2 A/AA and 2.1 AA rules. See `docs/ui_accessibility.json`. This does not replace manual accessibility testing.
- Desktop and mobile screens were visually inspected, with no page errors or horizontal overflow in the checked views.
- Dependency audit: zero vulnerabilities reported.

## Demo handoff

The previous interface's video, screenshots and local workspace were backed up under ignored `.tools/ui-v1/` before replacement. The refreshed recording uses the real production UI, backend and local Qwen model with labelled synthetic notes. Sarah remains the approved Kokoro voice. The refreshed video needs a new user YouTube upload before the DEV article can use a matching public demo embed.

The new silent recording lasts 91.00 seconds; the captioned narrated video lasts 112.36 seconds at 1920x1080. Audio/video durations match, all 27 saved caption cues reproduce the narration text, and the complete video decoded through FFmpeg. Local speech recognition recovered all spoken evaluation figures. The final video SHA-256 is `95a24c3217b73eb9742078f67ba2f64fa82162c3251fde34ec99d01a4ecad2ed`.
