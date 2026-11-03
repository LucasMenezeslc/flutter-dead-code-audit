# Cleanup Mode

Read this reference only after the user explicitly requests removal or cleanup.

## Authorization and selection

Only candidates reviewed as `remove` are eligible. Present their IDs and the recommended batch before editing. Do not silently include `retain`, `defer`, unreviewed, or “nearby” cleanup. Public API removal, generated-source changes, and flavor/platform removal require explicit confirmation of that scope.

## Batch rules

- Group only candidates with the same evidence and verification path.
- Keep batches small enough that a failure identifies the likely removal.
- Preserve behavior; do not combine cleanup with refactoring or feature work.
- Use recoverable version-control state and show the diff after each batch.

## Write-only state

Removing a write-only field normally requires removing its declaration and assignments, but not blindly deleting the surrounding operation.

- If an assignment shares a `setState` callback with live mutations, remove only the dead assignment.
- If the assignment is the only statement in `setState`, inspect whether the call intentionally forces a rebuild. Remove the wrapper only when no rendered value, controller value, inherited state, or lifecycle effect depends on that rebuild.
- Preserve listener removal, controller operations, logging, metrics, and other side effects surrounding the assignment.
- If the field appears to model visible behavior and a sibling implementation reads an equivalent field, stop and return it to Review as a possible incomplete feature.
- Verification must cover the affected interaction, not only analyzer success. For playback state, exercise play, pause, completion, replay, and route/lifecycle transitions as applicable.

## Removal sequence

1. Reconfirm references against the current tree; audit evidence can become stale.
2. Record the pre-removal analyzer/test status so existing failures are distinguishable.
3. Before editing, record the affected user flows, state transitions, lifecycle callbacks, routes, platforms, and flavors needed for the post-cleanup verification map.
4. Remove the narrowest confirmed unit. For generated code, update the owning source/configuration and regenerate through the project’s command.
5. Remove imports/exports made obsolete by that deletion, but no unrelated code.
6. Run formatting only on changed Dart files.
7. Run the analyzer, targeted tests, then broader tests/builds proportional to the candidate’s reach and supported flavor/platform matrix.
8. If verification fails or new dynamic usage appears, restore the batch and downgrade the finding; do not weaken tests.

## Completion report

List removed candidate IDs and files/symbols, diff summary, analyzer result, tests/builds run, unsupported variants not verified, and candidates intentionally retained. Then provide the developer-facing manual verification flows required by [verification.md](verification.md). Never claim a platform/flavor or manual flow was verified when it was not exercised.
