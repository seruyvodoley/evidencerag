# Stage 009 known-case regression

- Corpus: authored synthetic debugging fixture; not an independent efficacy set.
- Assessment: `sufficient`; answer: `answered`.
- Extracted values match fixture: `True`.
- Search iterations: 1; evidence chunks: 2; runtime: 9.035 ms.
- Every answer claim has a literal source chunk and mechanically re-extracted attribute/value.
- This is a functional regression check, not a semantic faithfulness or method superiority result.

Reproduce with a fresh output directory:

```sh
PYTHONPATH=apps/api .venv/bin/python -m packages.research.stage009_runner --output experiments/stage009/NEW_RUN
```
