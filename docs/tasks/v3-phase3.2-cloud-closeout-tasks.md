# V3 Phase 3.2 Tasks: Cloud Closeout

## 1. 准备

- [ ] 进入 `/root/video_project_src`。
- [ ] 阅读 `docs/specs/v3-phase3.2-cloud-closeout-spec.md`。
- [ ] 阅读 `docs/project-status/v3-phase3.2-cloud-compat.md`。
- [ ] 执行 `git status --short`。
- [ ] 区分 Phase 3.2 文件与历史无关 dirty files。

## 2. 验证

- [ ] 执行静态验证：

```bash
python -m py_compile cloud_backend/repository_interface.py cloud_backend/storage.py cloud_backend/postgres_repository.py cloud_backend/auth.py cloud_backend/main.py cloud_backend/dashboard_v11.py cloud_backend/teacher_pages.py cloud_backend/admin_pages.py cloud_backend/security.py cloud_backend/login_pages.py cloud_backend/reporting.py cloud_backend/ai_report.py cloud_backend/ui_style.py
```

- [ ] 如果服务已启动，执行运行验证：

```bash
API_BASE_URL="http://127.0.0.1:8011" bash scripts/validate_phase3_2_cloud_compat.sh
```

- [ ] 如果服务未启动，不要假写通过，状态文档保留 pending 并说明原因。

## 3. 状态文档

- [ ] 确认 `docs/project-status/v3-phase3.2-cloud-compat.md` 包含真实静态验证结果。
- [ ] 如果运行验证已执行，写入实际 markers。
- [ ] 如果运行验证未执行，明确记录 pending 原因。
- [ ] 记录残留问题，例如 sample 是否被 `.gitignore` 忽略。

## 4. Stage 文件

显式 stage Phase 3.2 云端文件。

建议文件：

```text
cloud_backend/postgres_repository.py
cloud_backend/dashboard_v11.py
cloud_backend/teacher_pages.py
samples/phase3_2_enhanced_result.json
scripts/validate_phase3_2_cloud_compat.sh
docs/specs/v3-phase3.2-cloud-compat-spec.md
docs/tasks/v3-phase3.2-cloud-compat-tasks.md
docs/prompts/v3-phase3.2-cloud-compat-cli-prompt.md
docs/runbooks/v3-phase3.2-cloud-compat-validation-runbook.md
docs/project-status/v3-phase3.2-cloud-compat.md
docs/specs/v3-phase3.2-cloud-closeout-spec.md
docs/tasks/v3-phase3.2-cloud-closeout-tasks.md
docs/prompts/v3-phase3.2-cloud-closeout-cli-prompt.md
```

如果 sample 被忽略且验证脚本依赖它：

```bash
git add -f samples/phase3_2_enhanced_result.json
```

禁止：

```text
git add .
```

## 5. 提交

- [ ] 执行 `git diff --cached --stat`。
- [ ] 确认 staged 文件没有无关历史改动。
- [ ] 提交：

```bash
git commit -m "feat(cloud): support phase 3.2 enhanced analysis fields"
```

## 6. 输出

完成后输出：

- 验证命令与结果。
- 运行验证是否通过或 pending。
- 实际提交哈希。
- 提交文件列表。
- `git status --short`。
- 未提交文件是否属于历史无关文件。
