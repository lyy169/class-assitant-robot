# Cloud Source Path Decision

## Purpose

This document records the recommended real path for the formal cloud source directory in sshfs mode.

In sshfs mode, files can be edited directly through the mounted filesystem, but terminal-only actions such as `mkdir`, `git init`, `git checkout`, `git add`, and `git commit` must be performed manually on the cloud server terminal.

## Recommended Source Path

Preferred path:

```text
/home/$USER/video_project_src
```

Example:

```text
/home/ubuntu/video_project_src
```

This path is recommended because it is:
- outside the running deployment directory
- suitable for Git management
- suitable for later remote repository binding
- less likely to mix source control with runtime-only state

## Running Directory Boundary

Current running deployment copy:

```text
/root/video_project
```

or the actual cloud-side path currently used as the deployment directory.

The source directory must not be created inside the running directory tree.

## Why Git Must Not Be Initialized In The Running Directory

`video_project/` currently mixes:
- active deployment files
- runtime data
- upload content
- logs
- local database artifacts
- old and new code paths

Initializing Git directly there would create the following risks:
- runtime data being tracked by mistake
- confusion between source changes and online state changes
- accidental overwrite of the deployment copy
- harder rollback and change review

## Why Source And Deployment Must Be Split

Using a separate source directory makes it possible to:
- manage code changes safely in Git
- keep runtime state out of version control
- review and rollback code changes cleanly
- prepare later deployment sync scripts without touching the online path directly

## Current Recommendation

Use this model:

```text
/root/video_project        # deployment copy, keeps running
/home/$USER/video_project_src   # formal source directory, Git-managed
```

This round only prepares the path decision and bootstrap artifacts. It does not switch any online service.
