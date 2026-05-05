# V3 Phase 3.2 Spec: Cloud Closeout

## 1. 目标

对 Phase 3.2 云端 enhanced JSON 兼容展示进行收口：确认 API/DB 边界、补齐运行验证、更新状态文档、按范围提交 git。

## 2. 收口范围

云端 Phase 3.2 预期文件：

- `cloud_backend/postgres_repository.py`
- `cloud_backend/dashboard_v11.py`
- `cloud_backend/teacher_pages.py`
- `samples/phase3_2_enhanced_result.json`
- `scripts/validate_phase3_2_cloud_compat.sh`
- `docs/specs/v3-phase3.2-cloud-compat-spec.md`
- `docs/tasks/v3-phase3.2-cloud-compat-tasks.md`
- `docs/prompts/v3-phase3.2-cloud-compat-cli-prompt.md`
- `docs/runbooks/v3-phase3.2-cloud-compat-validation-runbook.md`
- `docs/project-status/v3-phase3.2-cloud-compat.md`
- `docs/specs/v3-phase3.2-cloud-closeout-spec.md`
- `docs/tasks/v3-phase3.2-cloud-closeout-tasks.md`
- `docs/prompts/v3-phase3.2-cloud-closeout-cli-prompt.md`

如实际改动中包含额外 Phase 3.2 相关文件，必须先说明用途，再决定是否纳入提交。

## 3. 禁止事项

- 不使用 `git add .`。
- 不提交历史无关 dirty files。
- 不回滚用户或历史改动。
- 不做数据库迁移。
- 不重写 `POST /api/interaction-results`。
- 不新增必需 API。
- 不修改树莓派端或本地端。

## 4. 验证要求

静态验证：

```bash
python -m py_compile cloud_backend/repository_interface.py cloud_backend/storage.py cloud_backend/postgres_repository.py cloud_backend/auth.py cloud_backend/main.py cloud_backend/dashboard_v11.py cloud_backend/teacher_pages.py cloud_backend/admin_pages.py cloud_backend/security.py cloud_backend/login_pages.py cloud_backend/reporting.py cloud_backend/ai_report.py cloud_backend/ui_style.py
```

运行验证：

```bash
API_BASE_URL="http://127.0.0.1:8011" bash scripts/validate_phase3_2_cloud_compat.sh
```

如果服务未启动，必须在状态文档中明确记录 runtime validation pending，不得假写通过。

## 5. 状态文档要求

`docs/project-status/v3-phase3.2-cloud-compat.md` 必须记录：

- API 是否保持不变。
- DB 是否未迁移。
- raw JSON 是否保留 enhanced fields。
- detail API 是否返回 enhanced fields。
- dashboard/reports 展示内容。
- 静态验证实际结果。
- 运行验证实际 markers，或明确 pending 原因。
- 残留问题。

## 6. 提交要求

提交前必须：

- 输出 `git status --short`。
- 输出待提交文件列表。
- 显式 stage Phase 3.2 云端文件。
- 如果 `samples/phase3_2_enhanced_result.json` 被 `.gitignore` 忽略，且验证脚本依赖该样例，则只对该文件使用 `git add -f samples/phase3_2_enhanced_result.json`。

建议提交信息：

```text
feat(cloud): support phase 3.2 enhanced analysis fields
```

## 7. 验收标准

- 上传 API 路由保持不变。
- 数据库未迁移。
- raw JSON 保存 enhanced fields。
- detail API 和页面能消费 enhanced fields。
- 旧数据正常降级。
- 状态文档真实记录运行验证。
- git 提交只包含 Phase 3.2 云端范围。
