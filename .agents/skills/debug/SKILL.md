---
name: debug
description: Systematic debugging and incident investigation — reproduce, hypothesise, bisect, fix with a regression test. Use for bugs, failing tests, flaky tests, production errors, or "why is this slow/broken".
---
# /debug

1. **Reproduce** — get a failing command or test. No repro → gather evidence (logs, traces, metrics, request IDs) until you have one. Write it down.
2. **Bound** — what changed? `git log --since`, deploy history, config, dependency bumps, data shape. `git bisect run` when a known-good commit exists.
3. **Hypothesise** — list 2–3 candidate causes ranked by likelihood × ease of checking. Test the cheapest first.
4. **Observe, don't guess** — add a temporary log/assert or run a REPL; read the actual values. Remove temporary instrumentation after.
5. **Fix the cause, not the symptom** — and write the regression test that fails before the fix.
6. **Look sideways** — grep for the same pattern elsewhere; note them as follow-ups.
7. **Write up** (in the PR or incident doc): symptom, root cause, fix, why it wasn't caught, prevention.

Rules: two failed fixes for the same hypothesis → stop and summarise to the human. Production data/systems → read-only; any remediation on prod is T3.
Performance: measure first (`py-spy`, `EXPLAIN (ANALYZE, BUFFERS)`, request timing histograms) — never optimise without a number.
