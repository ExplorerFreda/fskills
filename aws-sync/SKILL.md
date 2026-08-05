---
name: aws-sync
description: Sync a local directory to or from S3 with a dry run, a backgrounded transfer, and a progress-tracking watch command. Usage: /aws-sync <upload|download> <local_dir> <remote_dir> [--region <region>] [extra aws s3 sync flags...]
---

Sync a local directory to or from S3, always dry-running first and running the real
transfer in the background so it survives terminal/session disconnects.

Parse the argument string:
- Token 1: mode, must be `upload` or `download`. If missing or not one of these two
  values, ask the user which mode they want rather than guessing.
- Token 2: `local_dir` (a local filesystem path).
- Token 3: `remote_dir` (the full S3 path, e.g. `s3://some-bucket/some/prefix`,
  including the bucket). Never hardcode a bucket name or path in this skill -- the
  bucket always comes from whatever the user passes as `remote_dir`.
- Remaining tokens: optional flags. Recognize `--region <value>` (default to
  `us-east-1` if not given); pass any other flags through verbatim to `aws s3 sync`.

Determine source and destination from mode:
- `upload`: source = `local_dir`, destination = `remote_dir`
- `download`: source = `remote_dir`, destination = `local_dir`

Derive a job name from the basename of `local_dir`, with any character outside
`[A-Za-z0-9_-]` replaced by `_`. Use it to name log files, always under `/tmp`:
- dry run log: `/tmp/aws_sync_<job_name>_dryrun.log`
- real transfer log: `/tmp/aws_sync_<job_name>.log`

Steps:

1. **Validate paths.**
   - `upload`: confirm `local_dir` exists (`ls -ld <local_dir>`). If it doesn't, stop
     and report -- do not create it.
   - `download`: create `local_dir` if needed (`mkdir -p <local_dir>`) since it's the
     destination.

2. **Dry run first, always.** Run in the foreground:
   ```
   aws s3 sync <source> <destination> --region <region> --dryrun [extra flags] > <dryrun_log> 2>&1
   ```
   Then get the file count with `wc -l < <dryrun_log>`.

3. **Report before doing anything real.** Tell the user the mode, source,
   destination, region, and the file count from the dry run. If the count is 0,
   report that everything is already in sync and stop -- do not proceed to step 4.

4. **Confirm before the real transfer.** This moves real data into or out of cloud
   storage and can overwrite existing objects/files, so always confirm with the user
   before proceeding past the dry run -- show them the file count and both paths.
   Do not skip this even if the user approved a similar sync earlier in the
   conversation; each new `local_dir`/`remote_dir` pair needs its own confirmation.

5. **Launch the real sync in the background**, once confirmed:
   ```
   nohup aws s3 sync <source> <destination> --region <region> [extra flags] > <real_log> 2>&1 &
   disown
   ```

6. **Give the user a progress command**, using the total captured in step 2:
   ```
   watch -n 5 'echo "<job_name>: $(wc -l < <real_log> 2>/dev/null || echo 0) / <total_from_dryrun>"'
   ```

Rules:
- Never hardcode an S3 bucket name or path -- it always comes from the `remote_dir`
  argument the user supplies.
- Never skip the dry run, and never start the real transfer without explicit user
  confirmation shown against that dry run's numbers.
- Keep all log files under `/tmp`.
