# help me codex skill

## Purpose

Use this skill when the user wants to fix a bug, implement a feature, modify existing behavior, add tests, or make a small-to-medium code change inside the current project.

This skill has two goals:

1. First, try to solve the task directly in Antigravity.
2. If the task cannot be solved confidently, produce a complete Codex handoff prompt that the user can paste directly into Codex.

The main priority is to save Codex tokens by doing broad project exploration, first-pass debugging, simple implementation attempts, and handoff compression inside Antigravity before escalating to Codex.

---

## Language Policy

When reporting to the user:

* Respond in Korean.
* Keep code, file paths, function names, class names, commands, logs, package names, API names, and error messages in their original language.
* Do not translate identifiers or terminal output.
* The Codex handoff prompt may be written in English for better coding-agent reliability, but it must explicitly instruct Codex to give its final explanation in Korean.

---

## Core Principle

Do not immediately escalate to Codex.

First:

1. Inspect the project.
2. Identify the relevant code path.
3. Attempt a minimal safe fix when appropriate.
4. Verify the result.

Only escalate to Codex when:

* The attempted fix failed.
* The root cause is still uncertain.
* The task involves high-risk logic.
* Multiple architectural assumptions need deeper verification.
* The change touches authentication, authorization, permissions, database, payment, security, data deletion, migration, caching, concurrency, or production-critical behavior.
* The implementation requires high-confidence reasoning beyond a simple patch.

---

## Workflow

### Step 1: Understand the task

Identify:

* What the user wants.
* Whether this is a bug fix, feature implementation, behavior change, refactor, test addition, UI adjustment, or investigation.
* The expected behavior.
* The current broken or missing behavior.
* Any risk areas.

If the user’s request is slightly ambiguous, make a reasonable assumption and continue. Do not stop unless the task is impossible without missing information.

---

### Step 2: Explore the project

Inspect only the files needed to understand the task.

Prioritize:

* Routes, pages, screens, or entry points related to the feature.
* Components directly involved.
* Hooks, stores, services, API handlers, queries, schemas, config files, and tests related to the behavior.
* Existing patterns for similar features.

Avoid unnecessary full-project exploration.

When possible, narrow the relevant files to 3–7 files.

---

### Step 3: Decide whether to attempt a fix in Antigravity

Attempt the fix directly when all of the following are true:

* The likely cause is clear.
* The change can be minimal.
* The affected files are limited.
* The behavior can be verified with tests, type checks, linting, build, or clear manual verification.
* The task does not involve high-risk areas such as auth, permissions, payment, database migration, sensitive data, destructive actions, production incident handling, or security-sensitive logic.

Do not attempt a risky or speculative large change just to avoid Codex.

---

### Step 4: Implement minimal changes

If attempting the fix:

* Make the smallest safe change.
* Follow existing code style and project patterns.
* Do not perform broad refactors.
* Do not rename unrelated files or symbols.
* Do not modify unrelated behavior.
* Add or update tests only when useful and aligned with the existing test structure.
* Preserve public APIs unless the user explicitly requested an API change.

---

### Step 5: Verify

After a change, run the most relevant available verification.

Prefer, in this order:

1. Targeted test for the affected area.
2. Existing test file related to the change.
3. Type check.
4. Lint.
5. Build.
6. Manual verification steps if automated verification is unavailable.

If a command cannot be run, explain why and provide the best manual verification steps.

---

## Success Output Format

If the task is solved confidently, output in Korean using this structure:

```markdown
# Antigravity Result

Status: Solved

## Summary

Briefly explain in Korean what was fixed or implemented.

## Changed Files

- `path/to/file`: what changed and why

## Verification

- Command or check performed:
- Result:

## Remaining Risks

- List any remaining risk, uncertainty, or manual check.
- If none, write: None identified.
```

Do not include a Codex handoff prompt when the issue is solved confidently.

---

## Failure or Uncertainty Output Format

If the task is not solved, only partially solved, or should be escalated to Codex, output in Korean using this structure:

````markdown
# Antigravity Result

Status: Needs Codex

## Why Codex Is Needed

Explain why this should be escalated.

## What I Confirmed

- Relevant fact 1
- Relevant fact 2
- Relevant fact 3

## Relevant Files

- `path/to/file`
  - Why it matters:
  - Important functions/components/routes/queries:
  - What Codex should check:

## Attempted Changes

- Describe any changes attempted.
- If no code was changed, write: No code changes were made.

## Failure / Uncertainty

- What still does not work:
- What is uncertain:
- Which assumptions may be wrong:

## Likely Root Causes

Rank the likely causes from most likely to least likely.

1. Cause:
   - Evidence:
   - Uncertainty:

2. Cause:
   - Evidence:
   - Uncertainty:

## Recommended Codex Reasoning Level

Choose one:

- Normal
- High
- Very High

Use:

- Normal: small UI, copy, style, simple validation, or single-file changes.
- High: failed bug fix, multi-file feature, state/API/data-flow issue, or unclear root cause.
- Very High: auth, permissions, DB, migration, payment, security, data loss, concurrency, cache invalidation, or production-critical behavior.

## Paste This Into Codex

```text
Recommended Codex reasoning level: [Normal / High / Very High]

You are working in Codex as a high-precision implementation agent.

Antigravity/Gemini already investigated or attempted this task. Do not blindly trust its conclusion. Critically review the analysis first, revise the plan if needed, and then implement the smallest safe fix.

Important rules:
- Do not start by scanning the entire project.
- First inspect the files listed below.
- If additional files are needed, briefly explain why before expanding scope.
- Prefer the smallest correct change.
- Do not perform unrelated refactors.
- Follow the existing code style and project patterns.
- Be conservative with authentication, authorization, permissions, database, payment, security, data deletion, migrations, caching, concurrency, or production-critical logic.
- After implementation, run the most relevant available tests or checks.
- If tests cannot be run, provide clear manual verification steps.

Language rule:
- Your final explanation to the user must be in Korean.
- Keep code, file paths, function names, class names, commands, logs, package names, API names, and error messages in their original language.
- Do not translate identifiers or terminal output.

Original user request:
[Copy the original user request here]

Antigravity result:
[Copy the Antigravity investigation result here]

Relevant files to inspect first:
[List files here]

Antigravity attempted changes:
[Describe attempted changes or write "No code changes were made."]

Known failure or uncertainty:
[Describe what failed or remains uncertain.]

Likely root causes:
[List likely causes with evidence.]

Your task:
1. Verify Antigravity's analysis against the actual code.
2. Identify any wrong assumptions or missing files.
3. Revise the implementation plan if needed.
4. Implement the fix or feature with minimal changes.
5. Run relevant tests/checks when possible.
6. Report the final changes and remaining risks.

Final response format:
1. Antigravity 분석 중 맞았던 부분
2. Antigravity 분석 중 틀렸거나 보완한 부분
3. 최종 수정 계획
4. 변경한 파일
5. 변경 요약
6. 테스트/검증 결과
7. 남은 위험 요소 또는 수동 확인 필요 사항
````

````

---

## Risk Escalation Rules

Escalate to Codex instead of forcing a fix when the task involves:

- Authentication
- Authorization
- Session handling
- Row-level security
- Database schema changes
- Data migration
- Payment or billing
- Subscription logic
- Personal or sensitive data
- Data deletion or recovery
- Security-sensitive behavior
- Cache invalidation
- Race conditions
- Concurrency
- Production incidents
- Large refactors
- Cross-cutting architectural changes

If any of these appear, the default Codex reasoning level should be Very High.

---

## Token-Saving Rules

The purpose of this skill is to reduce Codex token usage.

Therefore:

- Do broad exploration here, not in Codex.
- Compress findings before handoff.
- Limit relevant files to the smallest useful set.
- Separate facts from guesses.
- Include exact file paths and symbols.
- Include what was already tried.
- Include what Codex should verify first.
- Do not generate vague handoff text.

A bad handoff says:

```text
Check the dashboard logic.
````

A good handoff says:

```text
Start with `app/dashboard/page.tsx`, `lib/queries/userStats.ts`, and `components/dashboard/StatsPanel.tsx`.

The likely issue is that `userId` can be undefined before session loading completes, causing `getUserStats(userId)` to return an empty result.

Verify whether the query is gated by `enabled: !!userId` and whether the empty state is handled.
```

---

## Default Decision Rule

Use this simple rule:

```text
Antigravity solves first.
If solved confidently, stop.
If failed, uncertain, or risky, generate a Codex paste-ready handoff.
```

Recommended Codex reasoning level:

```text
Normal:
- Tiny UI changes
- Copy changes
- Style changes
- Simple validation
- Single-file obvious fix

High:
- Antigravity failed
- Root cause is unclear
- Multiple files are involved
- State, API, query, data flow, or tests are involved
- Feature implementation needs careful integration

Very High:
- Auth
- Permissions
- DB
- Migration
- Payment
- Security
- Data loss
- Race condition
- Cache invalidation
- Production-critical behavior
```

---

## Style

Be concise, direct, and evidence-based.

Do not over-explain unrelated code.

Do not hide uncertainty.

When escalating, produce a Codex prompt that is ready to paste without requiring the user to rewrite it.

Always respond to the user in Korean, except for code, paths, commands, logs, identifiers, package names, and error messages.
