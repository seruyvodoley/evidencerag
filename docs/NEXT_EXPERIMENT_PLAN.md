# План следующего независимого эксперимента

## Статус

В качестве внешнего кандидата для проверки пригодности выбран `Kajaluxan/version-aware-rag-corpus` (dataset card, revision `52a00d9`, CC BY 4.0 для курации/структуры; исходные документы наследуют лицензии проектов). Карточка сообщает о 882 Markdown files из 16 OSS проектов (50 distinct document families), 21,052 chunks и 628 QA по 6 типам; 14,550 change annotations указаны как LLM-extracted. Dataset card identifies CC BY 4.0 for curation/structure/evaluation; upstream docs retain their own licenses. Это заявленные авторами цифры, не независимая валидация. Это кандидат, не утверждённый benchmark: часть change annotations LLM-derived, качество gold-labels независимо не подтверждено, а текущий доступ Hugging Face может просить контактные сведения. Согласие на передачу данных/скачивание через такой gate не давалось; corpus не скачан и в репозиторий не включён.

`TimelyRAG` остаётся только supplementary candidate: repo не содержит обнаруженной лицензии на корпус/код, поэтому не использовать/распространять до уточнения прав. ContractNLI может дать дополнительную проверку текстовых evidence spans, но он не является temporal/version benchmark. Источники: https://huggingface.co/datasets/Kajaluxan/version-aware-rag-corpus , https://github.com/kaist-dmlab/TimelyRAG , https://stanfordnlp.github.io/contract-nli/ .

## До запуска

1. Зафиксировать revision, источник, лицензии каждого upstream документа, процедуру скачивания, privacy/contact gate и hash corpus snapshot.
2. Получить независимую выборку с изменениями числа/даты, добавлением, формулировочным перефразированием, отменой, противоречием и неустановимой применимостью. Не разметить любое diff как семантическое изменение.
3. Два независимых аннотатора размечают документ-версию, temporal validity, claims, supporting/contradicting/insufficient spans и rationale; третий adjudicates. Pilot 50–100 примеров, затем Cohen's kappa/Krippendorff alpha с confidence intervals и опубликованный guide.
4. Разделить по source/document family и времени, не допуская редакций одной семьи между train/dev/test. Предварительно зарегистрировать exclusions, seeds, queries, metrics и analysis.
5. Одинаковый offline Python harness для BM25 fixed-k (k=1/5/10), Adaptive-k, текущего EvidenceRAG controller, Oracle-version upper bound. Одинаковый retrieval corpus и budget: top-10 candidate pool, 3 search iterations, max 10 chunks, токеновый контекст, одинаковый wall-time/compute record. Протокол не должен ставить нечестные ограничения на baseline.
6. Хранить исходные JSONL answers, retrieval trace, exact evidence IDs/offsets/version/date, configs, code commit, env lockfile и raw logs с отдельным immutable run ID. Python ядро — authoritative for research; browser parity is a separate implementation check.
7. Retrieval: Recall@k, MRR, nDCG, evidence precision/recall. Temporal/version: correct-version rate, stale evidence rate, conflict/withdrawal detection, abstention when validity unknown. Sufficiency: expert labels + Brier/ECE only if calibrated probability exists. Answer quality only after a separately evaluated answerer; citation precision/coverage and unsupported-claim rate. Cost: #queries, chunks, tokens, latency, CPU/RAM. Report paired bootstrap CIs / paired randomization as pre-registered and correct for multiple primary comparisons.
8. Publish negative results and subgroup breakdowns; do not claim superiority or scientific novelty without pre-registration, independent labels, baseline validation, and literature review.

## Readiness

Python research modules and trace runner are present. One author-defined Stage 006 demonstration reproduces a second targeted retrieval but is not evidence of general efficacy. Independent corpus access/licensing, annotation, evaluation judge, statistical plan and full method matrix remain pending. No long-running experiment should run on GitVerse or VPS.
