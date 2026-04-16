# Cloud Src Bootstrap Runbook

## Purpose

This runbook explains how to execute the cloud source bootstrap in sshfs mode.

In this mode, the script is prepared through the mounted filesystem, but the actual bootstrap must be run manually on the cloud server terminal.

## Script To Run

Run this script on the cloud server terminal:

```bash
bash /root/video_project/scripts/bootstrap_cloud_src.sh
```

If the running deployment directory is not `/root/video_project`, open the script first and adjust the variables or provide environment overrides.

Recommended override example:

```bash
CLOUD_SRC_DIR="/home/$USER/video_project_src" RUNNING_DIR="/root/video_project" bash /root/video_project/scripts/bootstrap_cloud_src.sh
```

## What To Check Before Running

Confirm all of the following:

- the current online deployment directory is correct
- the source path does not point inside `video_project/`
- the target source directory does not already contain unrelated files
- no service switch or deployment action is bundled into this step
- you are running on the real cloud terminal, not only through sshfs file editing

## What The Script Does

The script will:

1. create a separate source directory
2. copy `cloud_backend/`, `docs/`, and `scripts/`
3. remove runtime-only data from the copied source tree
4. create `README.md`
5. create `.gitignore`
6. initialize Git inside the source directory
7. create branch `chore/cloud-src-bootstrap`
8. add files and commit the first bootstrap baseline

## What To Verify After Running

Check:

```bash
cd /home/$USER/video_project_src
git branch --show-current
git log -1 --oneline
git status
find cloud_backend -maxdepth 3 -type d -name data
find . -maxdepth 3 \( -name ".env" -o -name "*.log" -o -name "__pycache__" \)
```

Expected results:

- current branch is `chore/cloud-src-bootstrap`
- latest commit message is `chore: bootstrap cloud source repository`
- working tree is clean
- `cloud_backend/data/` is absent from the source directory
- no `.env`, runtime logs, or cache directories are tracked

## If The Script Fails

Safe rollback principle:
- do not touch `/root/video_project`
- only clean up the partially created source directory if needed

Example rollback:

```bash
rm -rf /home/$USER/video_project_src
```

Only do this if you have confirmed the path is the separate source directory and not the running deployment directory.

## Directories That Must Never Be Deleted By Mistake

Absolutely do not delete:

- `/root/video_project`
- `/root/video_project/uploads`
- `/root/video_project/instance`
- `/root/video_project/logs`
- `/root/video_project/cloud_backend/data`

These belong to the running deployment copy or runtime state.
