# Factory database recovery

Run `make prod-restore-drill FILE=backups/db/example.dump` to validate a trusted OMH backup. SQL and PostgreSQL custom dumps are supported. The recovery profile uses a separate PostgreSQL instance, Docker network and volume. The client verifies an adjacent checksum metadata file when present, restores into a newly created database, checks the OMH schema and reports its revision and table counts. The drill removes its temporary database after verification.

Run `make prod-restore FILE=backups/db/example.dump` to retain the restored database. Record the target name from the JSON report. On a separate recovery stack with external deliveries disabled, restore the matching export files and secret key, check the release revision, representative event IDs, artifact hashes and queue links, and test login and reads. Record the elapsed time.

For cutover, pause incoming traffic and workers, reconcile accepted messages and completed external deliveries against the backup boundary, then switch the application connection and files to the verified target. Start consumers after reconciliation. Keep the previous database and files available until the operator accepts the recovery.
