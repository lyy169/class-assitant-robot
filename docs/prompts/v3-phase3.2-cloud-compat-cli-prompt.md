# CLI Prompt: V3 Phase 3.2 Cloud Enhanced JSON Compatibility

请将本文件作为云端 CLI Codex 的执行提示词。

## 执行身份

你现在负责执行 Phase 3.2：云端兼容展示与验证。

工作目录：

```text
/root/video_project_src
```

## 必须先读

在改代码前必须阅读：

```text
docs/specs/v3-phase3.2-cloud-compat-spec.md
docs/tasks/v3-phase3.2-cloud-compat-tasks.md
```

## 阶段目标

云端兼容本地端 Phase 3.2 enhanced JSON。不要重构 API，不迁移数据库，不破坏旧数据。只做 optional 字段接收、raw 保存确认、detail 返回确认、dashboard/report 轻量展示和验证脚本。

## 严格边界

1. 不修改树莓派端。
2. 不修改本地分析端。
3. 不重写 `POST /api/interaction-results`。
4. 不修改 raw JSON 结构。
5. 不做数据库迁移。
6. 不新增必需 API。
7. 不破坏旧 JSON 上传。
8. 不破坏 Phase 2.9 登录权限。
9. 不执行 git commit。
10. 不使用 `git add .`。

## 必须先检查

1. `git status --short`。
2. 当前上传接口实现：
   - `cloud_backend/main.py`
   - `cloud_backend/storage.py`
   - `cloud_backend/postgres_repository.py`
3. detail API 实现：
   - `GET /api/teacher/results/{result_id}`
4. 页面实现：
   - `cloud_backend/dashboard_v11.py`
   - `cloud_backend/teacher_pages.py`
   - `cloud_backend/admin_pages.py`

## 兼容字段

Phase 3.2 字段全部 optional：

```text
analysis_version
algorithm_profile
quality_metrics
score_breakdown
curve_metadata
evidence_summary
enhanced_events
enhanced_issues
```

## API 要求

1. `POST /api/interaction-results` 保持不变。
2. 旧 JSON 可以上传。
3. 新 enhanced JSON 可以上传。
4. raw JSON 必须原样保存新增字段。
5. 数据库写入仍只依赖原有核心字段。
6. detail API 必须能返回 enhanced fields，或者保证 raw/detail 中能读到这些字段。
7. recent API 保持轻量，不强制塞入所有 enhanced fields。
8. status API 不变。

## 页面展示要求

### /dashboard

如果 result detail/raw 中存在 Phase 3.2 字段，展示“分析可信度/评分解释”区域，至少包括：

- `analysis_version`
- `quality_metrics.data_confidence`
- `score_breakdown` 五维分数
- `curve_metadata.window_seconds / smoothing`
- `evidence_summary` 中的视频、关键帧、音频、转写状态
- `enhanced_issues` Top 3

如果字段不存在，旧页面照常展示，不报错。

### /teacher/reports

如果有 `enhanced_issues`，报告详情中展示：

- 问题标签
- severity
- reason
- evidence
- suggestion

AI 未配置时不要假装 AI 已生成。规则报告和 enhanced_issues 可以作为“规则分析建议”。

### /admin/ingestion

可选展示：

- `evidence_summary.video_path_present`
- `standardized_video_present`
- `keyframe_count`
- `data_confidence`

如果实现成本高，可只在 detail/dashboard/reports 展示，admin ingestion 保持兼容即可。

## 样例

需要准备：

```text
samples/phase3_2_enhanced_result.json
```

如果本地端已经提供样例，请从本地端样例复制或让用户提供，不要凭空生成大量不真实数据。可以创建一个最小 enhanced 样例用于接口验证，但必须标记为 sample/demo。

## 验证脚本

新增：

```text
scripts/validate_phase3_2_cloud_compat.sh
```

脚本要求：

1. 接收 `API_BASE_URL`，默认 `http://127.0.0.1:8011`。
2. 上传 `samples/phase3_2_enhanced_result.json`。
3. 检查 HTTP 200。
4. 检查 raw saved_path 存在。
5. 检查 raw 文件包含 `"analysis_version": "3.2"`。
6. 调用 detail API，检查返回内容能看到 `quality_metrics` / `score_breakdown` / `enhanced_issues`。
7. 检查 `/dashboard` 页面可访问。
8. 检查 `/teacher/reports` 页面可访问。
9. 输出类似：

```text
PHASE32_CLOUD_UPLOAD_OK=true
PHASE32_RAW_PRESERVED=true
PHASE32_DETAIL_ENHANCED_FIELDS_PRESENT=true
PHASE32_DASHBOARD_OK=true
PHASE32_REPORTS_OK=true
```

## 文档

完成后新增：

```text
docs/runbooks/v3-phase3.2-cloud-compat-validation-runbook.md
docs/project-status/v3-phase3.2-cloud-compat.md
```

## 验证命令

建议执行：

```bash
cd /root/video_project_src
python -m py_compile cloud_backend/repository_interface.py cloud_backend/storage.py cloud_backend/postgres_repository.py cloud_backend/auth.py cloud_backend/main.py cloud_backend/dashboard_v11.py cloud_backend/teacher_pages.py cloud_backend/admin_pages.py cloud_backend/security.py cloud_backend/login_pages.py cloud_backend/reporting.py cloud_backend/ai_report.py cloud_backend/ui_style.py
API_BASE_URL="http://127.0.0.1:8011" bash scripts/validate_phase3_2_cloud_compat.sh
```

浏览器验收 URL：

```text
/login
/dashboard
/teacher/reports
/admin/ingestion
```

## 完成输出

完成后输出：

1. 修改文件列表。
2. API 是否保持不变。
3. DB 是否未迁移。
4. raw JSON 是否完整保存增强字段。
5. detail API 是否返回增强字段。
6. dashboard/reports 展示了哪些 Phase 3.2 信息。
7. 验证命令和验证结果。
8. `git status --short`。
9. 明确没有提交 git commit。
