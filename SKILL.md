---
name: flutter-dead-code-audit
description: Audit Flutter and Dart repositories for unused Dart declarations and potentially orphaned .dart files, rank candidates by evidence, and optionally remove confirmed dead code in verified batches. Use for dead-code reviews, unused-file investigations, cleanup planning, or validating whether Dart code can be deleted. Do not use for duplicate-code, asset, localization, or dependency audits.
---

# Flutter Dead Code Audit

Find candidates; do not equate “no static reference found” with “safe to delete.” Flutter and Dart projects contain generated entrypoints, flavors, conditional imports, registries, annotations, routes, platform channels, and public package APIs that can defeat a naive search.

## Choose the mode

- **Audit** is the default. Remain read-only except for an explicitly requested report file.
- **Review** turns findings into user decisions: remove, retain intentionally, or defer. Read [references/review.md](references/review.md). Review is mandatory before Cleanup.
- **Cleanup** applies only when the user explicitly asks to remove reviewed candidates marked `remove`. Read [references/cleanup.md](references/cleanup.md) before editing and [references/verification.md](references/verification.md) before reporting completion.

## Audit workflow

1. Establish scope from `pubspec.yaml`, workspace/package layout, `analysis_options.yaml`, build flavors, `main*.dart` entrypoints, generated-code conventions, and whether the repository publishes a package API.
2. Run `python3 <skill-dir>/scripts/audit_flutter_dead_code.py <project-root>`. The script requires Python 3.10+ and combines the SDK’s machine-readable analyzer diagnostics with deterministic import/export/part reachability. It uses FVM’s Dart binary when present and otherwise the Dart binary on `PATH`; it installs nothing. Treat its output as candidates, not verdicts.
3. If the repository defines a stricter analyzer wrapper, run it too. Do not install or reconfigure tooling during an audit.
4. For every candidate, perform the relevant checks in [references/false-positives.md](references/false-positives.md). Search the whole repository, including tests, native directories, generated configuration, scripts, and string references.
5. Classify candidates using the evidence rules in [references/audit-method.md](references/audit-method.md). Never report a generated file, public API, alternate entrypoint, platform implementation, or test-only helper as dead without resolving its ownership and consumers.
6. Before writing the result, read [references/report-design.md](references/report-design.md). Deliver a decision-oriented report with a short executive view and progressively disclosed evidence. Include exact file/symbol locations, evidence, confidence, false-positive checks performed, and the command that would verify a removal. Separate facts from inference.

## Review gate

After the audit, stop before editing. Present candidates in small reviewable groups and ask the user to choose `remove`, `retain`, or `defer` for each candidate or homogeneous group. A `retain` decision requires a reason; an optional review date prevents temporary compatibility, rollback, experiment, or migration code from becoming permanent by accident.

Do not hide retained code from future reports. Show it under **Intentionally retained**, together with its reason and whether its review date is due. When the user wants decisions persisted, use the JSON format in [references/review.md](references/review.md) and rerun the audit script with `--decisions <file>`. Do not create or commit a decisions file without permission.

## Evidence hierarchy

Use independent signals where possible:

1. Dart analyzer/compiler diagnostic, collected by the bundled audit script.
2. Import/export/part reachability from the inventory script.
3. Repository-wide symbol and string searches.
4. Runtime, route, DI, code-generation, platform, flavor, and public-API inspection.
5. Tests or builds demonstrating that a removal preserves supported behavior.

One missing reference is never enough. A high-confidence verdict normally needs at least two independent signals plus cleared false-positive checks.

## Report contract

The primary report is for making decisions, not for preserving raw tool output. Lead with the verdict, the next decision, and small action-based counts. Then organize candidates as:

- **Ready for review** — strong evidence and no plausible dynamic or external consumer.
- **Review carefully** — likely unused, but removal crosses a product, legal, platform, compatibility, or architecture boundary.
- **Needs team context** — intent cannot be proved from the repository.
- **Potential logic issue** — unreachable branches or unused values that may reveal a bug rather than cleanup.
- **Intentionally retained** — reviewed code kept for a documented reason; reopen when its review date is due or its evidence changes.
- **Not dead / excluded** — investigated candidates that are generated, test-only, conditional, externally consumed, or otherwise live.

Use a colored indicator together with a textual label; never rely on color alone. Keep the main view compact, group homogeneous mechanical findings, and move command output and exhaustive evidence into collapsible details or a technical appendix. Do not use tables wider than four columns or present dozens of full paths as an unbroken list.

For each candidate preserve `Location`, `Kind`, `Evidence`, `Checks`, `Confidence`, `Risk`, `Recommendation`, and `Verification`, even when some fields are collapsed. Do not pad the report with healthy files. When a report file is saved, also provide a compact navigable chat handoff with direct code references for the next review group. Follow the complete layout, link conventions, labels, grouping rules, and template in [references/report-design.md](references/report-design.md).

## Safety boundaries

- Do not delete, move, rename, deprecate, or modify code in Audit mode.
- Do not enter Cleanup until the user has reviewed and selected the candidate IDs to remove. Silence or a prior audit request is not removal approval.
- Do not change analyzer rules, regenerate code, edit `pubspec.yaml`, or alter CI without a separate request.
- Treat package exports as externally consumed unless repository and publishing context prove otherwise.
- Treat code used only by tests as test-only, not dead.
- Treat feature-flagged, platform-conditional, and flavor-specific code as conditional until the supported matrix is known.
- Never hand-delete generated output. Change its source/configuration and regenerate only when explicitly authorized.
- If evidence conflicts, lower confidence; do not average the conflict away.
