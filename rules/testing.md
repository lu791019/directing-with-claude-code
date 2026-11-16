# Testing Requirements

## Risk Tiers (decide BEFORE writing code)

A green run only proves the cases someone thought of passed. Test depth follows risk, not a uniform coverage number.
Record the tier in `implementation_plan.md` (see `~/.claude/templates/dev-workflow.md`).

| Tier | Typical scope | Required |
|------|---------------|----------|
| **High** | Money/payments, data loss or migration, outbound sends (email/post/webhook), auth/permissions, prod deploy | Acceptance criteria written first + tests written by a separate agent or the main session (not the implementer) + adversarial review + mutation sampling + Dex verifies by hand before release |
| **Medium** | Core feature logic, integrations, scheduled jobs | Acceptance criteria + unit/integration tests + main-session re-verification (do not trust agent self-report) |
| **Low** | Copy, styling, internal docs, one-off scripts | Feedback loop (run → test → lint) is enough |

Coverage (80% target) is a floor for Medium/High code, not evidence of correctness.

**The change sets the tier, not the author.** If the repo has a `REVIEW.md` with a `risk-paths` block, check it with `~/bin/risk-paths`: when planning (no diff yet) pass the files the plan will touch, `risk-paths --files <paths>`; when re-verifying, `risk-paths --base <branch>`. Exit 3 = High, and the plan may not lower it. Exit 0 = no hit, tier from the plan's judgment. **Exit 2 is an error** (missing block, git failure) — fix and rerun; never read it as "no hit". Repos without `REVIEW.md` → judge by the table above and mention that the repo has no path list.

## Test-Driven Development

MANDATORY workflow:
1. Write test first (RED)
2. Run test - it should FAIL
3. Write minimal implementation (GREEN)
4. Run test - it should PASS
5. Refactor (IMPROVE)
6. Verify coverage (80%+)

## Every Fix Leaves a Permanent Test

- Bug fix or prod incident → first write a test that reproduces it (RED), then fix (GREEN). The test stays forever.
- No reproducing test = the fix is not done.

## Who May Change Tests

- The agent fixing or implementing code must not loosen tests to get green. Dispatch fix/implement-only rounds with `TESTS=locked` on the first line; `~/.claude/hooks/test-edit-guard.sh` blocks their test-file writes and logs every subagent test edit to `~/.claude/logs/test-edits.jsonl`.
- If a test is wrong, the agent stops and reports which assertion and why; the main session decides.
- Bash writes (sed, redirects) bypass the hook — re-verification still reads `git diff` on test files.

## Is the Test Suite Itself Trustworthy? (High tier)

- Mutation sampling: temporarily break the code a new test locks → confirm RED → restore → confirm GREEN (dispatch-round §4 item 6).
- For a whole module, run a mutation tool on demand: Python `mutmut`, JS/TS `Stryker`. Surviving mutants = assertions that guard nothing.

## Reporting Results

Never report only a pass rate. List failures with their tier ("2 failed: both Low, copy") so Dex can decide on release.

## Troubleshooting Test Failures

1. Use **tdd-guide** agent
2. Check test isolation
3. Verify mocks are correct
4. Fix implementation, not tests (unless tests are wrong)

## Agent Support

- **tdd-guide** - Use PROACTIVELY for new features, enforces write-tests-first
