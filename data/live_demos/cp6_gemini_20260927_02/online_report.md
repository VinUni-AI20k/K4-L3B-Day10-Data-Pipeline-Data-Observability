# CP6 — Live demo online

Status: **complete**

Provider: gemini; requested model: `gemini-3.5-flash-lite`.
Pipeline run: `cp6_pipeline_20260927_04`.

Online answers below come from real tool-agent calls. Checks are deterministic; no LLM judge or heuristic fallback is used for these cases.

| Case | Baseline answer | Corrupted answer | Repaired answer |
| --- | --- | --- | --- |
| dropped_paper | 2026-07-22 | I don't know from the indexed corpus. | 2026-07-22 |
| stale_date | 2026-05-02 | 2025-05-02 | 2026-05-02 |
| stable_control | 2026-06-12 | 2026-06-12 | 2026-06-12 |
| absent_control | I don't know from the indexed corpus. | I don't know from the indexed corpus. | I don't know from the indexed corpus. |

The stale-date answer should follow the damaged index and be wrong against raw. This demonstrates silent data failure; repair restores the correct date. The dropped paper should cause abstention and recover after repair.

The separate ten-question offline benchmark remains extractive metadata QA/mock judging. These four online cases are a focused live demonstration, not a replacement full benchmark.

```json
{
  "baseline": {
    "samples": 4,
    "context_checks_passed": 4,
    "correct_against_raw": 4
  },
  "corrupted": {
    "samples": 4,
    "context_checks_passed": 4,
    "correct_against_raw": 2
  },
  "repaired": {
    "samples": 4,
    "context_checks_passed": 4,
    "correct_against_raw": 4
  }
}
```

Completion note: 11 accepted answers came from the initial Gemini attempt; the final case was retried successfully against the same sealed pipeline. The original failed attempt is preserved in prior_attempt_results.json; continuation_result.json records the retry. This was not an uninterrupted execution.
