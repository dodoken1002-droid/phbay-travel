# Webmaster V2 Pipeline

This repository uses an automated Webmaster V2 validation pipeline.

## Ordered flow

Observe -> Diagnose -> Isolated Worktree -> Code -> Test -> Review -> Commit -> Push -> Owner Merge

The automation must not merge directly to `main`. The owner remains responsible for merging.

Production deployment remains outside the V2 worker.
