# Audit Method

Use this reference when ranking findings or producing the report.

## Candidate classes

### Unused declarations

Functions, methods, classes, extensions, typedefs, variables, fields, constructors, and enum values that appear unreferenced. Prefer analyzer evidence and corroborating project-aware signals. Repository search is corroboration, not a parser.

#### Write-only mutable state

A field is write-only when it is initialized or assigned but its value is never read. This proves that the stored value cannot directly influence the current program, but it does not prove that the intended behavior is complete.

Treat write-only UI, lifecycle, playback, authorization, analytics, synchronization, or workflow state separately from mechanical unused declarations. Before recommending removal:

- inspect every assignment and its enclosing callback, `setState`, listener, transaction, or lifecycle method;
- check whether removing the assignment would also remove an intentional rebuild or other enclosing side effect;
- search sibling or predecessor implementations for the same field and determine whether they read it;
- ask whether the missing read represents an abandoned feature or a regression.

If a comparable active implementation reads the field, or the name represents visible behavior such as played, completed, authorized, submitted, or synchronized, classify it as **Review carefully** or **Potential logic issue**, not as a mechanical lint. State both conclusions explicitly: “the field is write-only in the current code” and “product intent remains unresolved.”

### Potentially orphaned Dart files

Files with no reachable import/export/part path from known entrypoints or package libraries. The inventory script reports graph evidence but cannot understand runtime registries or external package consumers.

### Unreachable branches

Branches proven impossible by the analyzer or by exhaustive language semantics. Do not infer unreachability merely because a product state looks unlikely.

### Stale commented code

Report separately as cleanup material, not executable dead code. Comments can contain historical or operational context.

## Confidence rubric

### High

All applicable conditions hold:

- analyzer or a project-aware Dart tool flags the declaration/file;
- no static, string, generated, native, test, flavor, platform, or tool reference exists;
- it is not public API or its consumers are proven in-scope;
- it is not generated and does not own generated output;
- a concrete analyzer/test/build verification command is known.

### Medium

Static evidence agrees and repository searches are clean, but an external consumer, dynamic registry, unsupported flavor/platform, or incomplete build context cannot be ruled out.

### Low

The finding relies mainly on naming, graph reachability, text search, or an incomplete tool run. Low-confidence findings belong under “Needs confirmation,” never “Confirmed unused.”

## Project-aware tool routing

Run only tools already available in the repository/environment.

1. Prefer project scripts documented in `README`, `CONTRIBUTING`, CI, Makefiles, Melos, or task runners.
2. Run `scripts/audit_flutter_dead_code.py`; it uses `dart analyze --format=machine` plus the bundled Dart-file graph inventory without adding a dependency.
3. Run the repository’s own analyzer wrapper as an additional signal when it differs from the standard analyzer.
4. Use `rg` when available, or an equivalent recursive text search, for exact symbol names, URI paths, route strings, channel names, annotations, and generated registration references.

Do not treat a clean analyzer as proof that public declarations or whole files are used; the standard analyzer intentionally has a narrower scope.

The bundled script is the dependency-free baseline. It reports SDK diagnostics for declarations the Dart analyzer can prove unused and graph candidates for files. Public declarations require repository/public-API analysis because “unused inside this checkout” is not equivalent to “unused by every consumer.”

## Scope for multi-package repositories

Audit each package from its own `pubspec.yaml`. Build a package-level summary afterward. A file can look unreferenced inside one directory while another workspace package imports its public API.

## Recommended summary table

| ID | Candidate | Kind | Confidence | Main evidence | Blocking uncertainty | Verification |
|---|---|---|---|---|---|---|

Use stable IDs such as `DC-001`. Follow the table with evidence details only for actionable candidates.
