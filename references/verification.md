# Post-cleanup Verification

Read this reference after applying an approved Cleanup batch and before reporting completion. The goal is to translate code removals into concrete behavior checks a developer can perform.

## Build the verification map

Map each removed candidate to the behavior it could have affected by inspecting its former callers, enclosing widget or service, route, state transitions, platform boundary, and neighboring live code. Group candidates by user flow rather than by file.

Do not invent a manual flow for a purely structural removal. Empty files, unused barrels, unused imports, and declarations with no runtime boundary normally need only analyzer/tests. Say **Manual flow: not applicable** and name the automated verification.

Require a manual flow when removal touches or sits inside:

- UI interaction or visible state;
- navigation, authentication, permissions, or legal consent;
- media playback, camera, upload, notifications, or platform channels;
- persistence, synchronization, retries, lifecycle, or background behavior;
- feature flags, flavors, platform-specific code, or dynamic registration;
- logic whose intent remained uncertain during Review.

## Flow format

Each flow must be executable by a developer without rereading the audit:

```markdown
### TF-01 · Media playback completion and replay

**Covers:** DC-032 · `_wasPlayed` cleanup
**Priority:** High
**Environment:** Android and iOS · screen containing a playable video
**Status:** Manual required — not executed by the agent

**Steps**
1. Open the media screen and start video playback.
2. Pause and resume from the overlay.
3. Let the video reach the end.
4. Attempt to replay it.
5. Navigate away and return; repeat after backgrounding the app.

**Expected**
- Play/pause icon matches actual playback.
- Completion does not leave the UI in a false “playing” state.
- Replay starts normally and audio state remains correct.
- No exception, frozen frame, duplicate audio, or stale listener appears.
```

Required fields:

- `Covers`: candidate or cleanup-group IDs;
- `Priority`: based on user impact and removal risk;
- `Environment`: platform, flavor, account/data state, permissions, and setup actually needed;
- `Status`: `Automated passed`, `Manual passed`, `Manual required — not executed`, `Blocked`, or `Not applicable`;
- `Steps`: concrete actions from a reachable entry point;
- `Expected`: observable results and important regression signals.

Add setup or cleanup instructions only when needed. Prefer one end-to-end flow that covers several related removals over repetitive per-file checks.

## Evidence and honesty

- Separate checks the agent executed from checks recommended to the developer.
- Never mark a manual flow passed based only on analyzer or unit-test success.
- Link each flow to the most relevant surviving file/line or route when the chat host supports code links. Removed lines can be referenced by candidate ID and diff summary.
- If product intent is unresolved, express the competing expected behaviors and mark the flow `Blocked` until the owner decides.
- When a supported platform, flavor, permission state, or account type was not exercised, list it explicitly.

## Completion layout

End Cleanup with three compact sections:

1. **Automated verification performed** — commands and actual results.
2. **Manual verification for the developer** — prioritized flows using the format above.
3. **Coverage gaps** — unsupported environments, unavailable devices/data, blocked intent, or checks not run.

Keep these sections in the Cleanup result or existing audit report. Create a separate test-flow file only when the user requests one.
