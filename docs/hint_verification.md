# Historical verification

These notes describe the November 2 version. Current behavior uses separate 3-second action waits, strict response schemas and a model-based input safety check for generation and feedback. Hints target 8–16 words and accept up to 20 within the 120-character cap. See the README for current behavior.

# Optional hint verification

The hint feature was added after the five-technique question comparison. It is not one of those five compared prompts.

## Local checks

21 tests pass in the existing uv environment. API transport is mocked in automated tests. Hint-specific checks cover context-only payloads, fixed model/provider routing, a 100-token cap, malformed/empty/multiline/over-120-character output, disabled configuration, shared cooldown, retained drafts on success/failure, retry, cached reuse and reset on question regeneration.

## Browser and live-service check, 2026-11-02

The existing app was tested at http://127.0.0.1:8501/ and the existing generated Python Developer / 5-year questions. No new question generation was needed. Three Get a hint buttons appeared. Existing drafts `test` and `test2` remained after hint retrieval and focus changes. This records the observed behavior of that version.

The first live hint for question 2 was valid under the initial 240-character policy but too long for the intended experience. The prompt and parser were then tightened to 120 characters and a 100-token output cap. The already cached first hint remains in that browser session; new question generation clears all hints. Two live hint requests total were made, with no automatic retry.

Final prompt SHA-256: `d36139991b2672924769603151ec6e62f812c44d1ff944c275cf9b441aaec8a6`.

Final-policy live check, question 1:

> With five years of Python experience behind you, how would you explain the way Python manages memory and concurrency, including reference counting, garbage collection and the GIL, and how those mechanisms influence your choice between threading, multiprocessing and asyncio in production services?

Returned hint:

> Start by tracing how an object lives and dies, then connect the GIL to CPU-bound versus I/O-bound workloads.

The app accepted and displayed this one-sentence hint; the button became disabled. Hints are plain text and can wrap according to screen width. Prompt instructions ask for English and a nudge rather than a full answer; structural validation does not guarantee language, factual quality or absence of answer leakage. This is one final-policy live sample, not comprehensive quality validation. No new OpenRouter billing-log inspection or exact cost measurement was performed.
