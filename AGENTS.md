# Job Search — Local Agent Instructions

This workspace is a lightweight job-search todo system.

Use natural-language commands from the user to update `TODO.md`.
Prefer deterministic behavior over clever guesses.

## Todo Dependency Model

Treat a task as a blocker only when the user expresses an explicit dependency.

A plain task add such as:
- "talk to francois"

means:
- add a normal active todo
- do not infer that it blocks anything

A dependency statement such as:
- "talk to francois before applying to any jobs"
- "don't apply to jobs until I talk to francois"
- "block job applications on talking to francois"

means:
- create or reuse a blocker todo for `talk to francois`
- find matching target todos
- move those target todos into `Blocked`
- mark each blocked item as blocked by `talk to francois`

## Deterministic Natural-Language API

Supported dependency intents:

- `X before Y`
- `do X before Y`
- `don't do Y until X`
- `block Y on X`

Interpretation:
- `X` is the blocker
- `Y` is the target task class or target task query

Supported unblock intents:

- `unblock Y`
- `I did X`
- `I finished X`
- checking off blocker `X` in the UI

Interpretation:
- `unblock Y` moves matching blocked tasks back to `Active`
- completing blocker `X` marks `X` done and auto-unblocks every task whose blocker is exactly `X`

## Canonical Blocker Title

Store blocker titles as short imperative todo text.

Normalization rules:
- lowercase for matching only
- trim whitespace
- strip leading phrases such as `i want to`, `i need to`, `i should`, `please`, `to`
- keep the user-facing text in natural form

Example:
- user says `I want to chat with Francois before applying to any jobs`
- blocker title becomes `chat with Francois`

Exact blocker matching uses the normalized blocker title.

## Deterministic `blocked-by` Syntax

Represent blocked tasks in `TODO.md` using a dedicated `## Blocked` section.

Each blocked line uses this exact format:

```md
- [ ] <task text> | blocked-by: <blocker title>
```

Example:

```md
## Blocked

- [ ] apply to [Perplexity role](https://jobs.ashbyhq.com/perplexity/4615ca06-bea7-47e3-9e57-f5cee52b75e6) | blocked-by: talk to francois
```

Rules:
- use exactly one blocker per blocked item
- do not leave blocked items in `Active`
- do not add `blocked-by` metadata to blocker tasks themselves
- when a blocked item is unblocked, remove the ` | blocked-by: ...` suffix and move it back to `Active`
- if a blocked item is auto-unblocked because its blocker was completed, preserve reversibility with hidden metadata so undoing the blocker can re-block it

## Matching Rules

Use conservative matching.
Only block items that clearly fit the target phrase.
If the match is ambiguous, ask the user instead of over-blocking.

Task-class mappings:

- `applying to any jobs`
- `applying to more jobs`
- `apply to jobs`
- `apply to more jobs`
- `job applications`
- `applications`
- `sending in more requests`
- `sending more requests`

These match todos that begin with:
- `apply to `
- `submit application`
- `send application`

- `followups`
- `follow-ups`

These match todos that begin with:
- `follow up`

- `referrals`

These match todos that contain:
- `referral`

If the target phrase is not a known class:
- fall back to case-insensitive substring matching against todo text
- only apply automatically when the match set is clear

## Example: What Blocks And What Does Not

Given this instruction:

- `talk to francois before applying to any jobs`

Create or reuse blocker:

- `talk to francois`

Block items like:

- `apply to Amazon Applied Scientist, Device Ad Products Personalization`
- `apply to Perplexity role`

Do not block items like:

- `follow up on Amazon referral`
- `get Microsoft referral from Michael`
- `follow up on OpenAI role email thread`
- `complete Mirendil take home`

Reason:
- those are not application-submit tasks
- they remain actionable unless the user names a broader target class

## Auto-Unblock Behavior

When blocker `X` is checked off or otherwise moved to `Done`:

1. Find every item in `Blocked` with `| blocked-by: X`
2. Move those items to the end of `Active`
3. Preserve their relative order from `Blocked`
4. Keep hidden `released-by: X` metadata on those active items
5. If blocker `X` is moved from `Done` back to `Active`, re-block every active item whose hidden `released-by` metadata is `X`

Example:

```md
## Active

- [ ] talk to francois

## Blocked

- [ ] apply to Foo | blocked-by: talk to francois
- [ ] apply to Bar | blocked-by: talk to francois
```

After checking off `talk to francois`:

```md
## Active

- [ ] apply to Foo
- [ ] apply to Bar

## Blocked
```

and:

```md
## Done

- [x] talk to francois
```

## Safety Rules

- Do not infer blockers from vague priority language such as `soon`, `later`, or `after that`
- Do not block broad sets of tasks unless the language is explicit
- If the user says `before applying to any jobs`, block only application-submit tasks, not all job-search activity
- If a request could reasonably match multiple categories, ask one short clarification question
