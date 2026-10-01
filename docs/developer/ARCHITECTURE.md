# Architecture

## System Overview

Describe the system in language a developer can understand without chat history.

## Primary Entrypoints

| Path | Purpose | Delegates to |
|---|---|---|
| TBD | TBD | TBD |

## Layers / Modules

Default conceptual layers where applicable:
- Domain/Core — pure business rules and models
- Application — use-cases/orchestration
- Integrations/Adapters — hosts/APIs/files/external systems
- UI — presentation and user interaction
- Infrastructure — persistence/runtime plumbing

Projects may use different names, but ownership must be explicit.

## Dependency Direction

State the allowed dependency direction. Domain/Core must not depend on UI or host APIs.

```
TBD
```

## Core Data Models

## Public Interfaces / Contracts

For each public boundary document inputs, outputs, units, optional/null semantics, errors and versioning.

## Data Flow

## External / Host Integrations

Each integration records adapter path, external system/version, permissions, failure behavior and fallback.

## Error Handling

## Logging / Diagnostics

## Security Boundaries

## Architecture Diagrams

## Known Constraints / Technical Debt

Important long-term decisions are recorded as ADRs under `docs/developer/decisions/`.

Keep `docs/developer/CODEBASE_MAP.md` synchronized with material module/entrypoint changes.
