# Code Review Standards

## Purpose

Code review ensures quality, security, and maintainability before code is merged. This rule defines when and how to conduct code reviews.

## When to Review

**MANDATORY review triggers:**

- After writing or modifying code
- Before any commit to shared branches
- When security-sensitive code is changed (auth, payments, user data)
- When architectural changes are made
- Before merging pull requests

**Pre-Review Requirements:**

Before requesting review, ensure:

- All automated checks (CI/CD) are passing
- Merge conflicts are resolved
- Branch is up to date with target branch

## Review Checklist

Before marking code complete:

- [ ] Code is readable and well-named
- [ ] Functions are focused (<50 lines)
- [ ] Files are cohesive (<800 lines)
- [ ] No deep nesting (>4 levels)
- [ ] Errors are handled explicitly
- [ ] No hardcoded secrets or credentials
- [ ] No console.log or debug statements
- [ ] Tests exist for new functionality
- [ ] Test depth matches the risk tier (see testing.md); bug fixes include a regression test

## Security Review Triggers

**STOP and use security-reviewer agent when:**

- Authentication or authorization code
- User input handling
- Database queries
- File system operations
- External API calls
- Cryptographic operations
- Payment or financial code

## Review Severity Levels

| Level | Label | Meaning | Action |
|-------|-------|---------|--------|
| CRITICAL | 重要 | Security vulnerability or data loss risk | **BLOCK** - Must fix before merge |
| HIGH | 重要 | Bug or significant quality issue | **WARN** - Fix, or close with a written reason |
| MEDIUM / LOW | 小意見 | Maintainability, style | **NOTE** - Max 3 per round; never dispatch an agent just to fix these |
| — | 既有 | Problem in lines this diff did not touch | Log as a todo; do not fix in this change |

既有 = the line is not in `git diff $(git merge-base <base> HEAD)` (from the fork point, so changes made on base after branching don't count; includes uncommitted work; check with `git blame` when unsure). It is still reported — a pre-existing money bug matters — but it does not block this change and is not the author's to fix here.

## Fresh-Context Review (Medium/High tier)

Before reporting a Medium/High change as done, have it reviewed by something that did not write it and does not share the conversation: a subagent given only repo path, base/head SHA, stated intent, and `REVIEW.md` — or `/code-review`. The main session re-reading its own diff does not count; it shares the same blind spots.

## Review Output Format

- First line is the count: `發現 N 則：重要 a／小意見 b／既有 c` — or `發現 0 則` when clean. Say so explicitly; silence is not a pass. The count must equal the findings listed.
- Second line is the read scope, mandatory: `讀檔範圍：整份讀了 <every touched file>；只看 diff：<files, with reason>（無則寫「無」）`. Every file in the diff must appear in one of the two lists. A file listed under 只看 diff means its 既有 problems were not checked — say so; do not claim 既有 0 for it.
- Read every touched file in full, not just the diff hunks — that is the only place 既有 problems surface.
- Every finding cites `file:line` and the input that triggers it. Do not infer behavior from a function name.
- Bug class: when one finding is an instance of a pattern (float money, missing null check), grep for every instance, list them all with the search command, and ask for the whole class to be fixed at once.
- Follow the repo's `REVIEW.md` (template: `~/.claude/templates/REVIEW.md`): its failure modes, skip paths, and nit limit override the defaults here.

## Review Convergence (review ⇄ fix loops)

An agent author fixes every nit it is given, so an unbounded loop never ends (Anthropic saw 50+ overnight rounds; most repeat flags were on code that existed before round 1).
- **Cap: 3 review→fix rounds.** If 重要 findings remain after round 3, stop and report to the main session/Dex to rethink the approach — do not run round 4.
- **Round 2+: review only `git diff <last-reviewed-sha>..HEAD`**, and pass the reviewer the list of findings already raised. Do not re-raise them; re-flag one only if the fix itself is wrong.
- Fix rounds address 重要 only. 小意見 and 既有 go to the todo list.
- Multi-round review by default is for High tier only; Medium gets one round plus a fix check.

## Agent Usage

Use these agents for code review:

| Agent | Purpose |
|-------|---------|
| **code-reviewer** | General code quality, patterns, best practices |
| **security-reviewer** | Security vulnerabilities, OWASP Top 10 |
| **typescript-reviewer** | TypeScript/JavaScript specific issues |
| **python-reviewer** | Python specific issues |
| **go-reviewer** | Go specific issues |
| **rust-reviewer** | Rust specific issues |

## Review Workflow

```
1. Run git diff to understand changes; read the repo's REVIEW.md if present
1b. Read every touched file IN FULL (not just hunks) — required to find 既有 problems; a review that only read the diff must say so as a limitation
2. Check security checklist first
3. Review code quality checklist
4. Run relevant tests
5. Verify test depth matches the risk tier (testing.md); check `git diff` on test files
6. Use appropriate agent for detailed review
```

## Common Issues to Catch

### Security

- Hardcoded credentials (API keys, passwords, tokens)
- SQL injection (string concatenation in queries)
- XSS vulnerabilities (unescaped user input)
- Path traversal (unsanitized file paths)
- CSRF protection missing
- Authentication bypasses

### Code Quality

- Large functions (>50 lines) - split into smaller
- Large files (>800 lines) - extract modules
- Deep nesting (>4 levels) - use early returns
- Missing error handling - handle explicitly
- Mutation patterns - prefer immutable operations
- Missing tests - add test coverage

### Performance

- N+1 queries - use JOINs or batching
- Missing pagination - add LIMIT to queries
- Unbounded queries - add constraints
- Missing caching - cache expensive operations

## Approval Criteria

- **Approve**: No CRITICAL or HIGH issues
- **Warning**: Only HIGH issues — each fixed, or closed with a written reason, before merge
- **Block**: CRITICAL issues found

## Integration with Other Rules

This rule works with:

- [testing.md](testing.md) - Test coverage requirements
- [security.md](security.md) - Security checklist
- [git-workflow.md](git-workflow.md) - Commit standards
- [agents.md](agents.md) - Agent delegation
