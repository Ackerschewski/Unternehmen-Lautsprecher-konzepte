# Code Structure Rules — Human-Readable by Default

## Goal

The repository must be understandable and maintainable by a normal human developer without needing prior chat history or an AI model to reconstruct intent.

A contributor should be able to answer:
- Where does the program start?
- Where is business/domain logic?
- Where are external/host integrations?
- Where is UI code?
- Where are data contracts and configuration?
- Where are tests for a given module?
- Which module owns a behavior?

using repository structure and documentation alone.

## 1. Dependency direction

Default logical direction:

```
entrypoints / UI
       ↓
application / use-cases
       ↓
domain / core
       ↑
integrations / adapters
```

Rules:
- Domain/Core must not import UI.
- Domain/Core must not directly depend on Blender, Inventor, Firebase, HTTP clients, filesystem UI frameworks or other host-specific APIs.
- UI calls application/domain contracts; it does not contain business logic.
- Host/external APIs are isolated behind adapters/contracts.
- Entrypoints stay thin and delegate immediately.
- Circular dependencies are not acceptable architecture.

Projects may use different folder names, but the dependency direction must be documented in `docs/developer/ARCHITECTURE.md`.

## 2. Recommended source layout

Use only the layers that make sense:

```
src/
  <package>/
    domain/          # pure models, rules, calculations
    application/     # use-cases / orchestration
    integrations/    # host/API adapters
    ui/              # views/controllers/panels
    infrastructure/  # persistence, files, runtime plumbing
    shared/          # genuinely cross-cutting small primitives
```

Avoid generic dumping grounds such as `misc`, `stuff`, giant `helpers`, or `utils` modules. If a helper has a domain purpose, name it after that purpose.

## 3. Module responsibility

- One module/file has one clear responsibility.
- One concept should have one canonical implementation.
- Public entrypoints are explicit.
- Internal implementation is not imported by unrelated modules as a shortcut.
- A new module must have a name that communicates its purpose without reading its source.
- Large modules are split by responsibility, not by arbitrary line count alone.

## 4. File-size guidance

For handwritten source:
- under 300 lines: preferred
- 300–500: acceptable
- over 500: review whether responsibilities should split
- over 800: split unless there is a documented reason
- over 1500: not allowed without an explicit architecture decision

Generated/vendor files are exempt and must be clearly identifiable.

## 5. Function and class design

- Functions do one job and have intention-revealing names.
- Prefer explicit inputs/outputs over hidden global state.
- Public functions/classes/contracts document non-obvious preconditions, units and failure behavior.
- Long functions are decomposed by responsibility.
- Classes are not used merely as namespaces for unrelated helpers.
- Side effects are obvious from naming and placement.
- Do not hide writes, network calls or host mutations inside apparently pure getters/calculations.

## 6. Naming

Use domain vocabulary from the specification.

Prefer:
- `calculate_ring_wall_thickness()`
- `BlenderMeshAdapter`
- `ProjectSubmissionReview`

Avoid:
- `doThing()`
- `process2()`
- `helper_new()`
- `finalFix()`
- `temp_manager`

Task IDs may appear in commits/tests/TODOs but should not become permanent domain API names.

## 7. Contracts and data models

At module boundaries:
- define explicit types/schemas/models,
- define units,
- define null/optional semantics,
- define error/failure semantics,
- define compatibility/version rules where persisted or external.

Do not pass unstructured dictionaries/maps across major boundaries when a stable data contract exists.

## 8. Configuration and constants

- Configuration belongs in a named config/profile layer.
- Domain/fabrication thresholds are not scattered magic numbers.
- Constants include unit/context in their names or surrounding model.
- Environment-specific configuration does not leak into domain code.
- Secrets never belong in source/config tracked by Git.

## 9. Errors and fallbacks

- Fail explicitly when correctness would otherwise be uncertain.
- No silent fallback that changes domain meaning.
- Translate external/host errors at adapter boundaries.
- Error messages contain actionable context without exposing secrets.
- Recovery behavior is documented if state may be partially changed.

## 10. Comments and documentation

Comments explain **why**, constraints, or non-obvious trade-offs—not line-by-line syntax.

Required discoverability:
- `docs/developer/CODEBASE_MAP.md` maps major modules and entrypoints.
- `docs/developer/ARCHITECTURE.md` states layers and dependency direction.
- Complex subsystem folders should contain a short README when their purpose is not obvious.
- ADRs record important long-term decisions.

## 11. Tests mirror behavior

Tests should be discoverable from the production module they protect.

Prefer:
- domain unit tests near/mirroring domain modules,
- adapter integration tests for host/external boundaries,
- regression tests for bugs actually found,
- explicit user/host/hardware acceptance steps where automation cannot prove behavior.

Do not create tests that merely duplicate implementation without asserting meaningful behavior.

## 12. Refactoring discipline

Before adding new code:
1. search for existing behavior,
2. identify the owning module,
3. extend the existing contract if appropriate,
4. only create a new abstraction when it has a clear independent responsibility.

Large refactors are separate tasks from feature delivery unless inseparable.

## 13. Human onboarding test

A developer unfamiliar with the project should be able to locate within roughly 10 minutes:
- primary entrypoint(s),
- main domain/core modules,
- main use-case/application flow,
- UI layer,
- external/host adapters,
- configuration,
- tests,
- build/run instructions.

If this requires reading chat history or guessing from filenames, the structure is not acceptable.

## 14. Review gate

A PR is not REVIEW_READY if it:
- adds duplicate logic,
- introduces an unexplained new layer,
- mixes UI/domain/host responsibilities,
- creates hidden side effects,
- leaves public behavior undocumented,
- makes the codebase harder to navigate without updating CODEBASE_MAP,
- creates a >800-line handwritten source file without documented justification.
