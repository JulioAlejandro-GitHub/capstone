# RESET.1B isolated rehearsal

This runner has no production execution option. It creates a new labelled PostgreSQL
container without published ports, host mounts or shared operational volumes. It refuses
an existing destination or a backup whose SHA-256 differs from the approved RESET.1
manifest. Operational database connections are restricted to read-only snapshots.

Run from the repository root with Docker available:

```sh
python3 scripts/reset/reset1b/run.py prepare --work /private/tmp/reset1b_new
python3 scripts/reset/reset1b/run.py classify --work /private/tmp/reset1b_new
python3 scripts/reset/reset1b/run.py rehearse --work /private/tmp/reset1b_new
python3 scripts/reset/reset1b/run.py finish --work /private/tmp/reset1b_new
python3 scripts/reset/reset1b/build_report.py --work /private/tmp/reset1b_new
```

`prepare` fingerprints all protected datasets/configuration and restores the archive referenced in `reset_1_full_history_manifest.json`.
It uses Docker PostgreSQL 17.9 tools and remaps operational schema DDL outside COPY
blocks; COPY values stay unchanged. The backend container supplies project Python
dependencies. Its database configuration is never redirected to the clone: connections
to the clone are constructed explicitly with private, randomly generated credentials.

`classify` reads the 414 deferred files. Exact identity references in adjacent
reports/manifests can establish an approved historical owner. Shared paths, coordination
files, project markers and unidentified ownership remain protected. It never assumes
ownership solely from membership in `outputs`.

`rehearse` checks all 97 restored table hashes; copies files to a private disposable
filesystem; runs the complete reset with an injected SQL failure; verifies database and
file recovery; repeats the complete reset and commits **only in the clone**. It restores
all original trigger function definitions before that commit. It then migrates the empty
clone through Alembic, checks OP1 Docker/Local and the ResultService authorization
boundary without training, testing, inference or a synthetic result backfill.

The shared connection factories supplied to the existing publication/deployment services
do not commit independently. A private deferred cache adapter applies invalidation only
after the database transaction commits. No live HTTP endpoint or global application cache
is invoked.

`maintenance.sql` is a template, not an operational migration. It requires validated clone
identity and a transaction-local allowlist of exact row hashes and primary keys. The runner
patches only the DELETE branch of existing BEFORE trigger functions for approved rows,
adds an operation scope trigger to every table, and restores/removes its own additions
before commit. Original FK/constraint triggers and AFTER audit triggers continue running.
New service/audit event IDs are admitted only after checking their exact originating
publication or approved deleted row; they are recorded in rehearsal evidence.

Original migrations, ResultService, retry rules, GlobalGate and operational deployments
are unchanged. `production_blocked.sql` always raises before DML in READ ONLY mode; there
is no approval environment variable or command-line switch that unlocks production.

Evidence is written to the private work directory: `restore.json`, `source_before.json`,
`files.json`, `rehearsal.json`, `source_after.json`, `finish.json`. Progress and fault details
are retained under the recorded temporary backend directory. Do not publish `target.json`
or `target.env`: they contain disposable credentials. A nonzero exit is a failed rehearsal,
not authorization to proceed. Rehearsal success also does not authorize an operational reset.

`finish` compares operational source/schema fingerprints and protected filesystem hashes,
then removes only the labelled disposable database and verified disposable copy trees.
`build_report.py` requires all completed evidence, including the unconditional production
SQL refusal, before creating the design and non-secret evidence deliverables.

`verify_commit_boundary.py` checks the final runner's exception branch with transaction
and filesystem doubles. A lost COMMIT acknowledgement leaves disposable copies in
`COMMIT_UNCERTAIN`; it never triggers an assumed rollback or automatic file restoration.
Real network interruption at COMMIT is not claimed as a completed database fault test.
