# Report Design

Use this layout for Audit and Review reports. The goal is to let a developer understand the state in under a minute, then inspect evidence only where a decision is needed.

## Design principles

1. Lead with decisions, not tools. Put tool versions, commands, resolver limitations, and raw diagnostics in the technical appendix.
2. Use progressive disclosure. The first screen contains the verdict, the decision queue, and risks. Detailed evidence belongs in candidate cards or `<details>` blocks.
3. Group repetition. Empty files, obsolete barrels, and mechanical analyzer lints should be summarized as homogeneous groups with an expandable member list.
4. Keep paths secondary. Use the symbol or short filename as the heading and show the full path on the next line in code formatting.
5. Pair every colored indicator with words so the report remains understandable in monochrome and by screen readers.
6. Distinguish cleanup from possible defects. Unreachable business logic belongs in **Potential logic issue**, not among safe deletions.
7. Do not call anything “safe to delete” before Review. Say “ready for review” or “recommended: remove.”
8. Write headings, labels, explanations, and suggested replies in the user's language. Keep commands, paths, analyzer codes, and decision values (`remove`, `retain`, `defer`) unchanged.

## Visual vocabulary

- 🟢 **Ready for review** — high confidence, normally low removal risk.
- 🟡 **Review carefully** — good evidence, but the code touches a sensitive boundary.
- 🟠 **Needs team context** — repository evidence cannot establish intent.
- 🔴 **Potential logic issue** — may be a bug; investigate before treating it as cleanup.
- 🔵 **Intentionally retained** — user or team chose to keep it with a reason.
- ⚪ **Not dead / excluded** — investigated and removed from the decision queue.

Confidence and risk are independent. Always write both as text, such as `Confidence: High · Removal risk: Medium`.

## Required structure

### 1. Title and one-sentence verdict

State repository, mode, and the main conclusion without implementation detail.

```markdown
# Dead-code audit · sample_app

**Audit only — no files changed.** Most findings are low-risk cleanup, with one platform-specific file and one template module requiring context.
```

### 2. Compact dashboard

Use at most four columns. Prefer action counts over detector counts.

```markdown
| Status | Candidates | What it means |
|---|---:|---|
| 🟢 Ready for review | 12 files + 4 declarations | Strong evidence; review in small batches |
| 🟡 Review carefully | 1 file + 1 declaration | Sensitive platform or product meaning |
| 🟠 Needs team context | 1 module | Confirm whether it is an intentional template |
| 🔴 Potential logic issue | 2 branches | Investigate as possible defects |
```

Analyzer totals and raw graph counts do not belong in this dashboard because they are not decisions.

### 3. Recommended decision order

Provide three to five short steps. Put zero-risk and homogeneous groups first; sensitive or ambiguous items last.

```markdown
## Suggested order

1. Review empty files and obsolete barrel files as one batch.
2. Review isolated unused widgets, helpers, and legacy screens.
3. Inspect platform-specific adapters and authorization state separately.
4. Ask the team whether `module_template` is an intentional scaffold.
5. Investigate unreachable checkout branches as a possible bug.
```

### 4. Decision groups

Organize by action and risk, not by which tool found the item. Each group begins with one sentence explaining why it exists.

For homogeneous mechanical findings, use a compact group card:

```markdown
### 🟢 G-01 · Obsolete compatibility barrels — 6 files

**Recommendation:** Remove as one batch

**Why:** Every feature exports its public API directly; no repository import uses the legacy barrel.

**Confidence:** High · **Removal risk:** None

<details>
<summary>Show the 6 files and verification</summary>

- `lib/features/orders/legacy_exports.dart`
- …

Checks: repository-wide imports, module barrels, analyzer.

Verify: `dart analyze` and the relevant Flutter test suite.
</details>
```

For an individual or sensitive finding, use a candidate card:

```markdown
### 🟡 DC-004 · LegacyPlatformAdapter

`lib/platform/legacy_platform_adapter.dart`

**Recommendation:** Confirm intent before removal

**Why it was flagged:** the class is never instantiated and its methods have no callers.

**Why caution is needed:** it looks like a platform fallback that may support an older runtime.

**Confidence:** High · **Removal risk:** Medium

<details>
<summary>Evidence, false-positive checks, and verification</summary>

- No imports, constructors, DI registrations, route references, or string references.
- Compared with the active adapter; no integration found.
- Before removal, confirm the fallback is not required by the supported platform matrix.
- After approved removal, run analyzer, platform tests, and the relevant smoke test.
</details>
```

Do not repeat identical evidence in every card. State shared methodology once and add only discriminating evidence per item.

### 5. Not dead / excluded

Keep this section short because it records investigation quality, not pending work. Show the candidate and the decisive reason. Collapse long lists.

```markdown
## ⚪ Not dead / excluded

- `generated_config.dart` — generated and used by an integration test.
- `shared_errors.dart` — consumed through the package barrel.
- 24 unresolved directives — audit-script path-resolution limitation, not project defects.
```

### 6. Review command

End the human-facing report with a concrete response format. Never ask the user to approve every item at once.

```markdown
## Your next decision

Start with the low-risk batch. Reply with, for example:

- `remove G-01 and empty files`
- `retain DC-004 — planned iOS workaround; review after 2027-02-01`
- `defer DC-043 — ask the team whether module_template is the scaffold template`
```

### 7. Technical appendix

Place the following here, preferably collapsed:

- exact commands and tool availability;
- repository scope, entrypoints, flavors, DI, routes, and codegen;
- raw candidate totals and analyzer diagnostic counts;
- full lint inventory;
- known tool limitations;
- exhaustive paths and line numbers;
- verification matrix.

The appendix preserves auditability without forcing every reviewer to read implementation detail.

## Chat response versus saved report

If a report file is saved, use a hybrid handoff: the report preserves the complete audit while the chat remains a navigable decision queue. Do not duplicate the full report in chat.

The chat response contains:

1. the one-sentence verdict;
2. the four action counts;
3. the highest-risk or ambiguous findings;
4. a link to the report;
5. the next small review group, with direct links to its code locations;
6. the exact `remove`, `retain`, or `defer` reply expected from the user.

### Navigable code references

For every candidate mentioned in chat, link to the most relevant repository-relative file and line. Prefer the host's native `relative/path.dart:line` code-reference syntax when it is clickable. Otherwise use a Markdown link whose label includes the short filename and line:

```markdown
[ios_camera_session.dart:1](lib/core/service/camera/ios_camera_session.dart#L1)
```

Use the declaration line when reporting a symbol, the diagnostic line for an analyzer finding, and line 1 only for a whole-file candidate with no better anchor. Never guess a line number: verify it immediately before writing the link. Do not link every item in a large mechanical group from chat; link the group in the report and at most three representative code locations.

### Chat handoff example

```markdown
Audit complete: 42 findings are ready for review; no code was changed.

**Review next — G-01: obsolete compatibility barrels**

- [legacy_exports.dart:1](lib/features/orders/legacy_exports.dart#L1) — unused compatibility barrel
- [legacy_exports.dart:1](lib/features/profile/legacy_exports.dart#L1) — same pattern
- 4 equivalent files are listed in the complete report

[Open the complete audit report](DEAD_CODE_AUDIT.md)

Reply with `remove G-01`, `retain G-01 — <reason>`, or `defer G-01 — <missing context>`.
```

Keep the navigable group to roughly three to seven links. On the next Review turn, show the next group with its code links; this creates an interactive review flow without making chat dense again.

Chat renderers may support a smaller Markdown subset than saved files. In chat, never emit raw HTML such as `<details>` or `<summary>`, and do not use a large table for candidate details. Use short headings and bullets instead. Collapsible HTML is allowed only inside the saved Markdown report after confirming that its intended renderer supports it; otherwise use ordinary headings there as well.

Markdown is the canonical portable format. Emoji indicators provide reliable visual scanning across Claude, Codex, terminals, and GitHub. If the user explicitly requests a richer artifact, an optional self-contained HTML view may add CSS colors, filters, search, and collapsible evidence, but it must preserve the same categories and must not become the only copy of the findings.
