# Stage 011B — document import

## Changes in this checkout

The upload dialog accepts multiple files, drag and drop, or a ZIP. A per-file queue exposes proposed title, family, version, effective date, document type and provenance, and allows edits before adding. A proposal with no explicit effective-date wording stays blank; it is never inferred from upload time, approval date or an unrelated historical deadline. Imported metadata can be edited later without replacing the original; the SQLite chunk index remains intact and revision links are rebuilt. Batch writes use one SQLite transaction and one revision-link rebuild.

ZIP handling is browser-local and streaming. It rejects absolute, traversal and backslash paths, symlinks, encrypted or unsupported compression, ZIP64/multi-disk archives, unsupported file types, nested archives, more than 20 documents, per-file output above 10 MB and total output above 25 MB. Actual emitted bytes are capped as well as declared directory sizes. This is defense in depth, not a claim that arbitrary hostile archives have been exhaustively fuzzed.

Metadata provenance is surfaced as `document_heading`, embedded PDF/DOCX metadata, first informative line, explicit text marker, filename marker, title suggestion or unresolved. Only explicit “действует с/вступает в силу с” dates create an effective-date proposal. User edits remain authoritative and editable. The post-upload editor exposes title, family, version, effective date, document type, explicit target document and the saved proposal provenance.

## Checks and measured local profile

Four parser/store tests cover explicit vs unknown effective dates, heading version/title/family proposals, batch indexing and rebuild after an explicit metadata edit. A Node smoke test accepted a two-file ZIP and rejected traversal and nested-archive samples. A local CPython 3.14.8 profile (3 runs; median; 4,202 bytes per generated Markdown document) measured parse + metadata / SQLite batch indexing:

| Documents | Parse + metadata | Batch index | Total |
|---:|---:|---:|---:|
| 1 | 0.36 ms | 2.50 ms | 2.86 ms |
| 3 | 0.94 ms | 3.67 ms | 4.62 ms |
| 20 | 6.00 ms | 14.29 ms | 20.29 ms |

These are small synthetic text documents on one development machine, not browser/PDF/DOCX/OPFS performance or an SLA. Pyodide startup and browser import did not complete in the observed Chromium session; therefore no claim is made about browser timing, end-to-end batch success or mobile behavior. Cancellation during an active Worker parse/index transaction, mass editing of an existing group, and per-file transactional recovery are also not yet implemented.
