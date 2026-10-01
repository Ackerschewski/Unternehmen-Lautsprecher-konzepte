# Backlog Hygiene Rules

## Goal

Keep task state usable by humans and agents without silently deleting history.

## Required cleanup

Before a new priority wave or CI reset:
- expired ACTIVE claims are reviewed and either refreshed, handed off, superseded or released;
- DONE work is not left in READY/IN_PROGRESS queues;
- duplicate tasks/issues are linked and one canonical item remains active;
- BLOCKED items name the blocking dependency or decision;
- REVIEW items have a reviewer/evidence request;
- stale derived dashboards are regenerated or marked stale;
- old integration branches are compared before reset/fast-forward;
- no abandoned task is silently resumed after its lease expired.

## Never automate blindly

Do not:
- delete tasks solely because they are old;
- mark tests PASS because a related task is DONE;
- clear a claim that contains unique unmerged work;
- close a defect without matching verification evidence;
- change portfolio allocation based on backlog pressure.

## WIP

One primary material work item per agent by default. Secondary review work must remain narrow and must not create a second implementation path.

## Evidence

Backlog state and evidence state are separate. `DONE` does not imply HOST_RUNTIME, USER_TEST or PHYSICAL PASS.
