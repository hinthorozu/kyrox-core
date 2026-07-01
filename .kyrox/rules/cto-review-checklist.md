# CTO Review Checklist

Use this checklist before approving any Pull Request.

## Scope Control

- [ ] PR matches the assigned task.
- [ ] No unrelated files were changed.
- [ ] No hidden refactor was included.
- [ ] Migration changes are justified.

## Architecture

- [ ] Domain layer is framework-independent.
- [ ] Application layer contains orchestration, not persistence details.
- [ ] Infrastructure implements ports/adapters.
- [ ] API layer does not contain business rules.
- [ ] Module boundaries are preserved.
- [ ] No circular dependencies were introduced.

## Domain Quality

- [ ] Entities protect invariants.
- [ ] Value objects validate their own rules.
- [ ] Domain exceptions are meaningful.
- [ ] Enums are placed in the proper domain module.
- [ ] Repository ports are defined in the domain/application boundary.

## Naming

- [ ] Backend naming is English.
- [ ] Database naming is English.
- [ ] API naming is English.
- [ ] Frontend user-facing text is Turkish.

## Tests

- [ ] Unit tests exist for domain behavior.
- [ ] Architecture tests exist when boundaries are affected.
- [ ] Integration tests exist when infrastructure/API behavior changes.
- [ ] All relevant tests pass.

## Security

- [ ] No secrets were committed.
- [ ] Auth/authorization rules were not weakened.
- [ ] Input validation exists where required.
- [ ] Sensitive data is not logged.

## Final Decision

- [ ] Approve
- [ ] Request changes
- [ ] Needs owner decision
