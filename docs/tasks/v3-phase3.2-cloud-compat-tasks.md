# V3 Phase 3.2 Tasks: Cloud Enhanced JSON Compatibility

## 0. 执行边界

- 只修改云端项目。
- 不修改本地端和树莓派端。
- 不重写上传 API。
- 不做数据库迁移。
- 不破坏旧 JSON 上传和页面展示。
- 不提交 git commit。
- 不使用 `git add .`。

## 1. 现状调查

- [ ] 检查 `git status --short`。
- [ ] 阅读 `docs/specs/v3-phase3.2-cloud-compat-spec.md`。
- [ ] 定位 `POST /api/interaction-results`。
- [ ] 定位 raw JSON 保存逻辑。
- [ ] 定位 repository 写入逻辑。
- [ ] 定位 `GET /api/teacher/results/{result_id}`。
- [ ] 定位 `/dashboard`、`/teacher/reports` 页面渲染逻辑。

## 2. 上传兼容

- [ ] 确认旧 JSON 上传仍成功。
- [ ] 确认 enhanced JSON 上传不因新增字段失败。
- [ ] 确认 raw JSON 原样保存新增字段。
- [ ] 确认 DB 写入只依赖原核心字段。

## 3. Detail API 兼容

- [ ] 检查 detail API 是否返回 raw 或完整字段。
- [ ] 如存在白名单过滤，将 Phase 3.2 optional fields 加入返回。
- [ ] 保持 API 外形尽量不变。
- [ ] 字段不存在时不报错。

## 4. 页面展示增强

### /dashboard

- [ ] 展示 `analysis_version`。
- [ ] 展示 `quality_metrics.data_confidence`。
- [ ] 展示 `score_breakdown` 五维分数。
- [ ] 展示 `curve_metadata` 关键说明。
- [ ] 展示 `evidence_summary` 证据摘要。
- [ ] 展示 `enhanced_issues` Top 3。
- [ ] 旧数据无 enhanced fields 时正常降级。

### /teacher/reports

- [ ] 如果存在 `enhanced_issues`，展示 reason/evidence/suggestion。
- [ ] AI 未配置时保持友好状态。
- [ ] 规则报告和 enhanced issues 关系清楚。

### /admin/ingestion

- [ ] 可选展示 evidence summary 和 data confidence。
- [ ] 如果不展示，至少保持兼容不崩。

## 5. 样例与验证脚本

- [ ] 准备 `samples/phase3_2_enhanced_result.json`。
- [ ] 新增 `scripts/validate_phase3_2_cloud_compat.sh`。
- [ ] 脚本上传 enhanced JSON。
- [ ] 检查 HTTP 200。
- [ ] 检查 raw 文件存在。
- [ ] 检查 raw 文件保留 `analysis_version`。
- [ ] 检查 detail API 能看到 enhanced fields。
- [ ] 检查 `/dashboard` 可访问。
- [ ] 检查 `/teacher/reports` 可访问。

## 6. 文档更新

- [ ] 更新或确认 `docs/specs/v3-phase3.2-cloud-compat-spec.md`。
- [ ] 更新本 tasks 文档。
- [ ] 新增 `docs/runbooks/v3-phase3.2-cloud-compat-validation-runbook.md`。
- [ ] 新增 `docs/project-status/v3-phase3.2-cloud-compat.md`，记录实际验证结果。

## 7. 输出要求

完成后输出：

- 修改文件列表。
- API 是否保持不变。
- DB 是否未迁移。
- raw JSON 是否完整保存增强字段。
- detail API 是否返回增强字段。
- dashboard/reports 展示内容。
- 验证命令与结果。
- `git status --short`。
- 明确没有提交 git commit。
