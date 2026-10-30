# Локальный браузерный runtime

The browser build vendors Pyodide 314.0.7, SQLite WASM 3.54.1, and pinned Python wheels so the document pipeline does not fetch runtime packages from PyPI/CDNs. `npm run build:local` copies the runtime and the checksummed wheel set to `public/vendor/`; generated output is ignored by git.

The wheel files are distributed under their upstream licenses, carried in each wheel's `.dist-info` metadata:

- Pyodide: Mozilla Public License 2.0.
- SQLite WASM: SQLite is public domain; the npm wrapper includes its own package license.
- pypdf: BSD 3-Clause.
- python-docx: MIT.
- pymorphy3 and `dawg2-python`: MIT.
- pymorphy3-dicts-ru: Open Russian Dictionary License (see wheel metadata).
- lxml: BSD 3-Clause.
- defusedxml: PSF License.
- pyparsing: MIT.
- setuptools: MIT.
- typing-extensions: PSF License.

The exact wheel filenames and SHA-256 hashes are generated in `browser-runtime-lock.json` in the static build. The local store lives in the browser's OPFS and its workspace token is kept in IndexedDB. Neither stores document bytes in `localStorage` or `sessionStorage`.
