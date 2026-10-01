# Developer Onboarding

This page is for a developer who has no chat history and no prior knowledge of the project.

## 1. What this project does

TBD — 3–6 sentences.

## 2. Run / build

- prerequisites: TBD
- install: TBD
- run: TBD
- test: TBD

## 3. Architecture in one minute

TBD — summarize the major layers and dependency direction.

## 4. Primary entrypoints

- application/add-on entrypoint: TBD
- UI entrypoint: TBD
- integration/host entrypoint: TBD

## 5. Where common changes belong

| Change | Module / Path |
|---|---|
| Domain rule / calculation | TBD |
| Feature/use-case | TBD |
| UI | TBD |
| External/host integration | TBD |
| Configuration / presets | TBD |
| Tests | TBD |

## 6. Important contracts

- TBD

## 7. Known constraints

- TBD

## 8. Before opening a PR

- read the concrete task,
- run local relevant tests,
- run `python tools/validate_project.py`,
- update `CODEBASE_MAP.md` if module boundaries changed,
- document new public contracts / ADRs,
- leave required user/host/hardware tests as explicit gates rather than claiming PASS.
