# Baseline, corrupted, and repaired comparison

All three evaluations use the saved test set `../eval/test_set.json` with 10 questions.
Frozen test set SHA-256: 19d5ac3b18cab70db178c29a7bac72328f386c375e9df1abe12459fb3b4dd03f

| Measure | Baseline | Corrupted | Repaired |
| --- | ---: | ---: | ---: |
| Documents | 24 | 20 | 24 |
| Evaluated questions | 10 | 10 | 10 |
| Retrieval Hit Rate | 100.00% | 80.00% | 100.00% |
| Mean Token F1 | 1.0000 | 0.8000 | 1.0000 |
| Answer source Hit Rate | 100.00% | 80.00% | 100.00% |
| Grounded Token F1 | 1.0000 | 0.8000 | 1.0000 |
| Abstention rate | 0.00% | 20.00% | 0.00% |
| Heuristic judge answers | 10 | 10 | 10 |
| Judge accuracy | 100.00% | 80.00% | 100.00% |
| Mean judge score / 5 | 5.00 | 4.20 | 5.00 |
| Quality gate passed | True | False | True |
| GX expectations passed | 7/7 | 3/7 | 7/7 |
| Stale papers | 1/24 (4.17%) | 2/20 (10.00%) | 1/24 (4.17%) |
| Freshness SLA passed | True | True | True |

## Failed quality checks

- Baseline: none
- Corrupted: expect_table_row_count_to_be_between, expect_column_values_to_be_unique (paper_id), expect_column_value_lengths_to_be_between (title), expect_column_value_lengths_to_be_between (summary)
- Repaired: none

## Repair and benchmark interpretation

- Repaired clean records were checked against the saved baseline records and rebuilt twice from the raw snapshot.
- Repaired answers and retrieved document IDs were checked again against the same collection and questions.
- Corrupted quality failure triggers repair; repaired quality must pass before publishing its index.
- Missing explicit paper references abstain. Grounded Token F1 is zero when the answer source is not the reference DOI.
- Judge fallback is heuristic; its accuracy must not be presented as independent LLM evaluation.
- 10/10 questions quote a DOI. The QA code gives an exact DOI match priority in retrieved results, so Hit Rate can remain high even when the corrupted corpus fails quality checks.
- The table reports observed scores; it does not assume corruption lowered them or repair raised them.
