# Cloud Steady-State Choice Template

Use this template to record the current long-term runtime choice for the cloud backend.

Do not mark `systemd` as active unless the operator has actually installed and verified the service on the Linux server.

## 1. Current Choice

- choice: `foreground` / `systemd`
- decision date:
- decided by:

## 2. Choice Rationale

- why this mode is being used now:
- current constraints:
- why the other mode was not chosen yet:

## 3. Current Formal Port

- formal port: `8011`

## 4. Current Formal Backend

- backend: `sqlite`
- raw fallback: `enabled`

## 5. Latest Health / Recent / Dashboard Check

- health:
  - date:
  - result:
- recent:
  - date:
  - result:
  - fallback_to_sample:
  - latest analysis_id:
  - latest source_kind:
- dashboard:
  - date:
  - result:
  - title marker:
  - raw badge marker:
  - latest analysis_id marker:

## 6. Raw / SQLite State

- raw directory latest files:
- SQLite file path:
- SQLite file size:
- optional SQLite row check:

## 7. Operator Notes

- runtime notes:
- known caveats:
- next scheduled review:

## 8. If Switching to systemd

Prechecks:

- foreground runtime verified on `8011`
- `.env.runtime` confirmed
- service example confirmed
- no conflicting foreground process on `8011`

Operator steps:

```bash
cp /root/video_project_src/cloud_backend/classroom-cloud-backend.service.example /etc/systemd/system/classroom-cloud-backend.service
systemctl daemon-reload
systemctl enable classroom-cloud-backend.service
systemctl start classroom-cloud-backend.service
systemctl status classroom-cloud-backend.service
journalctl -u classroom-cloud-backend.service -n 100 --no-pager
```

Post-switch checks:

```bash
ss -lntp | grep 8011
curl -i http://127.0.0.1:8011/health
cd /root/video_project_src
bash scripts/check_cloud_runtime_observability.sh
```

## 9. If Staying on foreground

Required operator discipline:

- start only with:

```bash
cd /root/video_project_src
bash scripts/deploy_cloud_backend.sh
```

- keep one authoritative runtime terminal or `tmux`/`screen` session
- after restart, always rerun:

```bash
ss -lntp | grep 8011
curl -i http://127.0.0.1:8011/health
cd /root/video_project_src
bash scripts/check_cloud_runtime_observability.sh
```

- stop the old process before starting a new one
