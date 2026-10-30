# Offline synthetic retrieval pilot

Split: test; 21 queries per configuration; 8 configurations.
The corpus is author-created synthetic data. It is useful for controlled regression checks, not independent empirical evidence.

| Configuration | Evidence recall | Required-span coverage | Same-edition conflict F1 | Version-change F1 | Mean chunks |
|---|---:|---:|---:|---:|---:|
| fixed_k | 1.000 | 1.000 | 1.000 | 1.000 | 2.619 |
| fixed10_sensitivity | 1.000 | 1.000 | 1.000 | 1.000 | 2.905 |
| adaptive_k_score_gap | 1.000 | 1.000 | 1.000 | 1.000 | 2.095 |
| sufficiency_guided_no_judge | 1.000 | 1.000 | 1.000 | 1.000 | 2.905 |
| proposed_evidencerag | 1.000 | 1.000 | 1.000 | 1.000 | 2.810 |
| without_version_awareness | 1.000 | 1.000 | 0.889 | 0.000 | 2.905 |
| without_literal_conflict_signals | 1.000 | 1.000 | 0.000 | 0.000 | 2.810 |
| without_iterative_expansion | 1.000 | 1.000 | 1.000 | 1.000 | 2.810 |

No semantic sufficiency judge or answer generator ran. Answer correctness, false abstention, unsupported answers and faithfulness are null by design; the previous False Abstention=1.0 was an artifact of treating an absent formal-rule answer as a generated answer refusal.
The score-gap top-k is an FTS5 BM25 heuristic inspired by adaptive context sizing; it is not a replication of Adaptive-k, which uses dense similarity thresholds. The sufficiency-guided configuration records UNKNOWN because no judge is installed, then expands retrieval within the common budget.
The proposed controller is an engineering prototype that preserves dated version differences and same-edition literal disagreement separately. It is not a validated new method. There are only a few independent synthetic evaluation clusters; no confidence interval or significance claim is reported.
Every trace includes content-derived evidence IDs, source position, version/date, retrieval score, chosen evidence and controller reasons. Variable wall-clock measurements are retained in raw outputs.
