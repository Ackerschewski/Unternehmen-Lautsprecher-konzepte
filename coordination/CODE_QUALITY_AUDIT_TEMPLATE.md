# Code Quality Baseline Audit

## Scope

- Repository:
- Revision:
- Auditor:
- Date:
- Languages / host:

## 1. Architecture / boundaries

Findings:
- Domain/UI separation:
- Host/API isolation:
- Dependency direction:
- Circular coupling:
- Duplicate implementations:

## 2. Discoverability for a human developer

- Entrypoints obvious:
- CODEBASE_MAP accurate:
- Naming quality:
- Module responsibilities:
- Public contracts discoverable:
- Build/test instructions usable without chat history:

## 3. Maintainability

- oversized files/modules:
- oversized/complex functions:
- hidden global state:
- magic constants:
- silent fallbacks:
- error handling:
- TODO / dead-code debt:

## 4. Tests / evidence

- domain/unit coverage quality:
- adapter/integration tests:
- regression tests:
- real host/runtime evidence:
- user/manual gates:
- tests that are misleading or too coupled to implementation:

## 5. Security / supply chain

- secrets:
- dependency risk:
- tool/runtime permission risk:
- unsafe external execution:
- logging/privacy concerns:

## Findings

| ID | Severity | Area | Evidence | Required action |
|---|---|---|---|---|
| CQ-001 | TBD | TBD | path:line / behavior | TBD |

## Refactor plan

1. Critical correctness/security issues
2. Boundary/architecture issues blocking future work
3. Human discoverability/documentation
4. oversized/duplicated modules
5. opportunistic cleanup

## Baseline decision

- Safe to continue feature work unchanged:
- Feature work allowed with guardrails:
- Refactor gate required before new features:
- User/host validation required:
