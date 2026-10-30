# Diagnostic trace: stage 006

One already executed diagnostic run, not a benchmark. Corpus: two author-written synthetic editions in `datasets/demo/service-*`. It tests the actual SQLite/FTS5 adapter, explicit authored exact-quote sufficiency rule, version-targeted follow-up retrieval, and literal-citation validation.

- Search calls: 2; stop reason: `sufficient`.
- New evidence chunks returned across calls: 2; distinct source revisions: 2.
- Newly supported formal claims: 1.
- Answer: `answered`, exact quote only; verification `literal_citation_checked`.
- Semantic evaluation, free-form answer generation, correctness/faithfulness metrics: not run (`null` / unavailable).
- No external API was called. The output is not evidence of real-world answer quality or method superiority.

Reproduce with:

```sh
PYTHONPATH=apps/api .venv/bin/python -m packages.research.trace_runner --output experiments/NEW_OUTPUT_DIRECTORY
```

The command requires a new output path and refuses to overwrite one. See `config.json` for input and source hashes; `trace.json` contains each action, version filter, assessment, returned IDs, new documents/chunks/claims and the final citation-checked extract.
