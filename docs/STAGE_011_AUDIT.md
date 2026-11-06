# Stage 011 audit — 03.11.2026

## Scope and evidence

The checkout's source HEAD is `cf98bba91ec94a02274fca2e9d1eab713e50acd6`, matching `origin/master`. The working tree already contained the in-progress Stage 011A changes from the preceding turn; this turn continued that work. The original three user documents were not available in the checkout. The Stage 011 fixture therefore records only the exact amendment text and facts included in the user's request, marked synthetic. It is not an exact-document or independent evaluation.

No VPS, TunnelDeck, Caddy, SSH, WireGuard, DNS or shared network configuration was accessed or changed.

## Reproduced causes

- Deadline extraction treated dates in one passage as competing values without assigning roles. The old deadline in “instead of 18 November … by 30 November” could survive as a current fact, and effective dates/source-edition dates could enter the same candidate set.
- Amendment recognition did not cover the supplied verbs “изменён/перенесён” with “вместо … необходимо/принимается”. Attribute replacement was therefore missed or old and new values were evaluated together.
- Revision indexing leaned on title/family text and a narrow set of old-value patterns. Explicit target edition, clause and old-value proof were not retained as a complete link relation; audit metadata could be lost during deduplication.
- The result header read `result.trace.length` although research iterations live in `research_trace.trace`.
- `sufficient` was possible before a complete linked-revision catalog check.

## Work completed in this checkout

Typed date roles and exact spans, partial attribute operations, stronger explicit link evidence and ambiguity handling, a revision audit gate, iteration and claim counts, conservative metadata proposals, one-transaction batch indexing, metadata edits, and bounded local ZIP import have been implemented. Regression and measurement details are in [version fix](STAGE_011_VERSION_FIX.md), [import UX](STAGE_011_IMPORT_UX.md) and [evaluation](STAGE_011_EVALUATION.md).

## Acceptance state

Python regression suite and browser type-check/build pass. A Node smoke test accepted a two-file archive and rejected traversal and nested ZIP samples. Production Chromium loaded the UI and presented all three ZIP entries. A dedicated Playwright run then spent 120 seconds waiting for metadata analysis to finish; the browser fetched the Pyodide runtime, pinned wheels and SQLite WASM but the local Worker did not return. The precise stall within SQLite initialization/OPFS setup is not yet isolated. Thus the ZIP-to-index workflow, persistence-after-refresh, full query/citation flow and desktop/mobile acceptance are **not verified**. The original documents were unavailable, and the negative amendment matrix is not yet complete. This milestone is not accepted and has not been published.
