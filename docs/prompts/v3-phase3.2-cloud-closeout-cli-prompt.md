# CLI Prompt: V3 Phase 3.2 Cloud Closeout

请将本文件作为云端 CLI Codex 的收口提示词。

## 执行身份

你现在负责对 Phase 3.2 云端 enhanced JSON 兼容展示进行验证和 git 收口。

工作目录：

```text
/root/video_project_src
```

## 必须先读

```text
docs/specs/v3-phase3.2-cloud-closeout-spec.md
docs/tasks/v3-phase3.2-cloud-closeout-tasks.md
docs/project-status/v3-phase3.2-cloud-compat.md
```

## 收口目标

- 确认 API/DB 边界：上传 API 不变，DB 不迁移。
- 确认 raw JSON、detail API、dashboard/reports enhanced fields 兼容。
- 补齐或更新状态文档。
- 显式 stage Phase 3.2 范围文件。
- 提交一个云端 Phase 3.2 commit。
- 不带入历史无关 dirty files。

## 严格禁止

- 不使用 `git add .`。
- 不回滚用户或历史改动。
- 不提交无关 dirty files。
- 不做数据库迁移。
- 不重写 `POST /api/interaction-results`。
- 不修改本地端或树莓派端。

## 执行步骤

1. 进入 `/root/video_project_src`。
2. 输出当前目录和 `git status --short`。
3. 阅读状态文档，确认 Phase 3.2 实际完成内容。
4. 执行静态验证：

```bash
python -m py_compile cloud_backend/repository_interface.py cloud_backend/storage.py cloud_backend/postgres_repository.py cloud_backend/auth.py cloud_backend/main.py cloud_backend/dashboard_v11.py cloud_backend/teacher_pages.py cloud_backend/admin_pages.py cloud_backend/security.py cloud_backend/login_pages.py cloud_backend/reporting.py cloud_backend/ai_report.py cloud_backend/ui_style.py
```

5. 如果服务已启动，执行运行验证：

```bash
API_BASE_URL="http://127.0.0.1:8011" bash scripts/validate_phase3_2_cloud_compat.sh
```

如果服务未启动或环境不满足，不要假写通过；在状态文档中保留 pending 并说明原因。

6. 如果验证输出和状态文档不一致，更新：

```text
docs/project-status/v3-phase3.2-cloud-compat.md
```

7. 显式 stage Phase 3.2 云端文件：

```bash
git add cloud_backend/postgres_repository.py
git add cloud_backend/dashboard_v11.py
git add cloud_backend/teacher_pages.py
git add scripts/validate_phase3_2_cloud_compat.sh
git add docs/specs/v3-phase3.2-cloud-compat-spec.md
git add docs/tasks/v3-phase3.2-cloud-compat-tasks.md
git add docs/prompts/v3-phase3.2-cloud-compat-cli-prompt.md
git add docs/runbooks/v3-phase3.2-cloud-compat-validation-runbook.md
git add docs/project-status/v3-phase3.2-cloud-compat.md
git add docs/specs/v3-phase3.2-cloud-closeout-spec.md
git add docs/tasks/v3-phase3.2-cloud-closeout-tasks.md
git add docs/prompts/v3-phase3.2-cloud-closeout-cli-prompt.md
```

如果样例文件未被忽略，执行：

```bash
git add samples/phase3_2_enhanced_result.json
```

如果样例文件被 `.gitignore` 忽略，且验证脚本依赖该样例，执行：

```bash
git add -f samples/phase3_2_enhanced_result.json
```

8. 输出 `git diff --cached --stat`，检查 staged 范围。
9. 如果 staged 范围只包含 Phase 3.2 云端文件，提交：

```bash
git commit -m "feat(cloud): support phase 3.2 enhanced analysis fields"
```

10. 输出提交哈希和 `git status --short`。

## 完成输出

完成后输出：

1. 验证命令与结果。
2. 运行验证是否通过或 pending。
3. 是否更新状态文档。
4. 实际提交哈希。
5. 提交文件列表。
6. 剩余 `git status --short`。
7. 如果仍有未提交文件，说明是否为历史无关文件。
