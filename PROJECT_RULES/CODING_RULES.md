# Coding Rules

These rules apply together with `PROJECT_RULES/CODE_STRUCTURE_RULES.md` and `coordination/CODE_QUALITY_POLICY.yaml`.

## Core principles

- Prefer small, clearly named functions/classes with one responsibility.
- One source file should have one coherent responsibility.
- Search existing implementation before adding new behavior.
- Do not duplicate domain logic.
- Do not hide side effects or silent fallbacks.
- Avoid magic domain constants; use named config/profile values.
- Public boundaries document inputs, outputs, units and failure semantics.
- UI must not own domain logic.
- Host/platform code must be isolated behind adapters.
- TODOs require a task/bug/tech-debt ID.
- Large refactors get their own task unless inseparable from the feature.
- Comments explain why/constraints, not obvious syntax.
- Permanent API/module names use domain language, not chat/task names.

## File size guidance

Handwritten source:
- < 300 lines: preferred
- 300–500: acceptable
- > 500: responsibility split review required
- > 800: split unless explicitly justified
- > 1500: not allowed without an accepted architecture decision

Generated/vendor files are exempt and must be clearly identifiable.

## Human readability gate

A normal developer without chat history must be able to navigate the repository using:
- README
- `docs/developer/DEVELOPER_ONBOARDING.md`
- `docs/developer/CODEBASE_MAP.md`
- architecture and module names

If understanding requires reconstructing intent from AI chat history, the code/documentation is incomplete.
