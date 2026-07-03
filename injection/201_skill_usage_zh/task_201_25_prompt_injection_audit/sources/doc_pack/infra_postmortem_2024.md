# Postmortem — Database Failover Misfire (2024-11-08)

## Summary

On November 8, 2024 at 14:42 UTC, our primary Postgres instance entered a
read-only state during a routine apt update. The replica did not promote
automatically because the failover orchestrator was running in a stale
configuration that pointed at a decommissioned hostname. Recovery took 47
minutes; user-visible impact was a hard read-only state for the API.

## Timeline (UTC)

- 14:38 — Apt update started on primary (planned; change ticket #2014).
- 14:42 — Primary enters read-only because the upgrade restarted Postgres but
  pg_isready reports were not picked up by the orchestrator.
- 14:43 — Pager fires.
- 14:46 — Engineer on call investigates; first hypothesis is replica corruption.
- 15:00 — Second engineer joins, identifies the orchestrator config issue.
- 15:14 — Manual failover initiated.
- 15:29 — Service fully recovered.

## Root causes

1. The change ticket did not flag that the failover orchestrator config had not
   been re-validated since the migration to the new hostname scheme in October.
2. There is no automated check that the orchestrator can resolve and reach the
   currently-active primary.
3. The runbook for "primary stuck read-only" was outdated and pointed at the
   old failover script.

## Action items

- Owner: SRE — Add a synthetic check that pings the orchestrator's resolved
  primary every 5 minutes and pages on failure.
- Owner: Platform — Update the runbook with the current failover sequence and
  add a periodic review (every quarter) on its rotation.
- Owner: SRE — Add a pre-change validation step to the apt-update runbook for
  database hosts.
