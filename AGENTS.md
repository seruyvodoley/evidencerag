# EvidenceRAG / «Основание»

Read README.md and docs/PROJECT_STATUS.md before changes. Preserve user data, unrelated checkouts and TunnelDeck infrastructure. Never alter VPN, routes, firewall, DNS, SSH or shared proxy configuration without explicit scope and review. Do not use secrets in logs, commits, browser code or reports.

Use frontend-design for intentional UI work and web-design-guidelines for review. Design tokens and three evaluated concepts are in docs/DESIGN_SYSTEM.md. Main language is Russian.

Python 3.12+, uv sync; web: npm ci in apps/web. Checks: .venv/bin/pytest -q; npm run check and npm run build in apps/web. Start: scripts/start.sh. Production serves built assets through FastAPI. Offline experiments: PYTHONPATH=apps/api .venv/bin/python -m packages.research.runner --output experiments/<new-run> --split test. Never overwrite run directories. Do not run heavy experiments on the VPN VPS.

All search signals are lexical heuristics unless an explicit authored formal rule applies. Do not call text matches entailment, synthesized fixtures empirical scientific evidence, or this method superior to S2G-RAG. Public LLM routes are deliberately absent. Keep workspace scoping on every read/write/download and keep citation validation strict.

After a significant milestone, update docs/HANDOFF_FOR_CHATGPT.md, docs/TESTING.md and docs/PROJECT_STATUS.md with actual measured results and blockers. Commit completed work locally. Do not claim public deployment, VPN end-to-end health, Docker validation or semantic faithfulness without checking them.
