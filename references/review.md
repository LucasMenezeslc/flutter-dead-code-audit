# Review Decisions

Use this reference after an audit and before any cleanup.

## Decisions

- `remove`: the user accepts the evidence and authorizes this candidate for a later Cleanup operation. It does not itself authorize deletion during the Review turn unless the user also explicitly asks to apply it.
- `retain`: the code is intentionally present. Require a concrete reason. Use `review_after` when the reason is temporary.
- `defer`: evidence or product context is incomplete. Record what would resolve it and optionally a review date.

Review candidates in small groups. Do not ask the user to approve a large undifferentiated deletion list. Show location, purpose if known, confidence, risk, and recommendation.

## Durable decisions file

Persist decisions only when requested. Use JSON so the bundled audit script can validate and join decisions deterministically:

```json
{
  "version": 1,
  "decisions": [
    {
      "key": "file:unreachable_from_known_roots:lib/legacy/old_screen.dart",
      "disposition": "retain",
      "reason": "Rollback implementation for checkout migration CHK-204",
      "review_after": "2027-02-01"
    }
  ]
}
```

The audit output contains the exact candidate keys. Never invent a key from memory.

Required fields:

- `key`: exact key emitted by the audit script.
- `disposition`: `remove`, `retain`, or `defer`.
- `reason`: required for `retain` and `defer`; recommended for `remove`.

Optional fields:

- `review_after`: ISO date (`YYYY-MM-DD`). A due decision returns to review; it is not silently discarded.
- `reference`: ticket, ADR, migration, incident, owner, or other evidence.

Run:

```bash
python3 <skill-dir>/scripts/audit_flutter_dead_code.py <project-root> --decisions <decisions.json>
```

The script reports matched decisions, unreviewed candidates, decisions due for review, and stale decisions whose candidate no longer exists. Retained candidates stay visible; the decision file is not a suppression list.

## Reopen a decision

Re-review when:

- `review_after` is due;
- the candidate’s key changes because its location/evidence changed;
- the referenced ticket, rollout, migration, or compatibility promise ends;
- supported flavors/platforms or package publication status changes;
- tests or runtime evidence contradict the recorded reason.

