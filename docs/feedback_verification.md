# Historical verification

These notes describe the November 2 version. Current behavior uses separate 3-second action waits, strict response schemas and a model-based input safety check for generation and feedback. Hints target 8–16 words and accept up to 20 within the 120-character cap. See the README for current behavior.

# Optional answer feedback verification

This feature was added on 2026-11-02. It is separate from the five-technique question comparison and does not establish completion of every optional bonus.

Each answer has Get feedback. Only an explicit click sends the selected question, its generation-time role/experience and that answer to Claude Sonnet 5.5 through the existing OpenRouter/Anthropic route. Other drafts and hints are not included. Feedback is short English practice guidance, not a score or hiring decision. The prompt asks for a supported strength and one improvement, or a respectful explanation when the answer cannot be assessed. The parser checks JSON and a single text value of 5–400 characters; it cannot guarantee semantic correctness or exactly two sentences.

The button is disabled for empty answers, after cached success or without configuration. Editing the corresponding answer removes stale feedback. All API actions share the existing 15-second session cooldown. Failures retain questions, drafts and hints; retries are manual. New question generation clears all feedback.

## Automated checks

26 tests passed in the existing uv environment. The added tests use mocked transport and cover selected-answer payloads, fixed routing/token cap, empty/overlong inputs, malformed responses, explicit send, cache, editing invalidation, preserved other drafts, cooldown, failure/retry and regeneration reset. Existing question/hint tests still pass.

## Live browser check

The existing app was tested session with Python Developer / 0 years, the first generated question about list/tuple/dictionary and the existing draft `test`. One live Get feedback request succeeded. No draft was edited for this check. The returned feedback was:

> Your answer, "test", is too brief to assess, so I can't point to a strength yet. Try starting with one sentence defining each type (list, tuple, dictionary), then add a short example from a study or personal project where you picked one and why.

The button became disabled with Feedback received. Existing hints and drafts stayed visible. This short-answer sample does not establish overall feedback quality. No new billing-log inspection or exact cost measurement was performed.

Prompt SHA-256: `a4eeb7fd42d9f6b201508d24f2eb1e950bb794ce262acd9e13b857bb128d23cd`.
