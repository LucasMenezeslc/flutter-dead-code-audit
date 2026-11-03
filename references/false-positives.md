# Flutter and Dart False Positives

Read the sections relevant to each candidate. These checks prevent “unused” from becoming an unsafe deletion claim.

## Entrypoints and supported variants

- `lib/main.dart`, `lib/main_*.dart`, `bin/*.dart`, `tool/*.dart`, examples, benchmarks, integration tests, and custom build scripts.
- Flutter flavors supplied with `--target`, CI matrices, launch configurations, Xcode schemes, Gradle product flavors, and deployment scripts.
- Background entrypoints annotated with `@pragma('vm:entry-point')`, isolates, notification handlers, and callback dispatchers.

## Language and module mechanics

- `export`, `part`, and `part of` relationships.
- Conditional imports/exports using `dart.library.io`, `dart.library.html`, or custom environment constants.
- Deferred imports and code reached only on a supported platform.
- Top-level files under `lib/` that form a published package API.

## Code generation and registries

- Files owned by `build_runner`, Freezed, json_serializable, Riverpod generator, injectable, Drift, Retrofit, go_router builders, localization generation, mocks, and plugin registrants.
- Annotation-driven consumers where the generated reference is absent until codegen runs.
- Registrations assembled through generated barrels or maps.

Never delete a generated file directly. Determine whether its annotated source/configuration is obsolete and whether regeneration is authorized.

## Flutter runtime indirection

- Named routes, router tables, deep links, navigation keys, and string route names.
- Dependency-injection/service-locator registration and lookup by type or name.
- `MethodChannel`, `EventChannel`, `BasicMessageChannel`, Pigeon, FFI symbols, native plugin registration, and callbacks referenced from Android/iOS/macOS/Windows/Linux/Web code.
- Widget builders, callbacks stored in maps, serialization discriminators, and factories selected by enum/string/config.
- Feature flags, remote config, experiments, permissions, and paid/role-gated screens.

## Tests and tooling

- Unit/widget/golden/integration tests, fixtures, fakes, test utilities, and screenshot harnesses.
- DevTools extensions, build scripts, migrations, seeders, benchmarks, and one-off operational tools.
- A file referenced only by tests is **test-only**. Decide whether the test capability remains required before considering deletion.

## Public and external consumers

- A package’s `lib/<package>.dart` and any exported symbol may be used by downstream repositories unavailable to the audit.
- Plugins and federated implementations can be selected by pub metadata instead of a Dart import visible in the same package.
- Examples can be contractual documentation for a published API.

When external consumption is possible, classify as “Needs confirmation” unless versioning, publication, and consumer scope are explicitly known.

## Search checklist

For a candidate, search as applicable for:

- declaration name and constructor variants;
- relative path, `package:` URI, export barrel, and generated filename stem;
- route/deep-link strings and registry keys;
- annotation names and expected generated outputs;
- platform-channel names and native symbol references;
- flavor targets, CI commands, launch configurations, and scripts;
- tests, examples, benchmarks, and workspace sibling packages.
