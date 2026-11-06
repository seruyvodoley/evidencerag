# Stage 011 evaluation — incomplete acceptance

## Automated checks

- `.venv/bin/pytest -q`: **98 passed**, one existing Starlette/httpx deprecation warning.
- `npm run check`: **0 errors, 0 warnings**.
- `npm run build:local`: successful production browser bundle; local Pyodide runtime and pinned wheels bundled.
- Chromium opened the production build and showed the new upload dialog. A dedicated desktop Playwright test parsed a three-document ZIP into three queue entries. It then waited 120 seconds for metadata analysis; the Worker fetched Pyodide, its pinned wheels and SQLite WASM but did not return. The precise stall within SQLite initialization/OPFS setup is not isolated. The test failed before any document was committed. No question was answered and no persistence-after-refresh assertion was completed.
- A separate Node smoke test of the streaming ZIP helper accepted two supported files, rejected a traversal path and rejected a nested ZIP.

The browser page was also resized to 390×844 during a development-server session, where the strict CSP blocks Vite's development-injected styles. That image is not accepted as mobile visual verification. Production mobile E2E was not completed.

## Functional result available from Python

The authored synthetic Stage 011 regression checks 2025 and 2026 temporal values and requires four claim slots after the exact amendment supplied in the prompt. It passes, including citation/evidence ID assertions. The three original user documents were not available, so Stage 011's exact-source acceptance criterion is unmet. No metadata precision/recall or unsupported-autofill rate is estimated; the test set is too small and authored for this implementation.

## Performance profile

See [import UX report](STAGE_011_IMPORT_UX.md). Measured CPython synthetic Markdown cases are 2.86 ms (1 file), 4.62 ms (3), and 20.29 ms (20), including parsing, metadata suggestion and batched SQLite indexing. These measurements exclude browser/WASM startup and are not representative of PDF/DOCX or mobile storage.

## Publication and remaining gates

No source commit or GitVerse Pages artifact was created. Existing public URL remains whatever is currently served; this work does not verify it contains Stage 011. Before publication: diagnose the local Worker initialization stall; complete ZIP import, query, citations, metadata edit, index rebuild and refresh persistence in production Chromium; repeat at mobile viewport; test the hostile ZIP cases and full amendment negative matrix; obtain/use exact source documents or explicitly revise that acceptance requirement. No VPS, VPN, proxy, SSH or DNS changes were made.
