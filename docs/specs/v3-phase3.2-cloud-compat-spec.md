# V3 Phase 3.2 Spec: Cloud Enhanced JSON Compatibility

## 1. 阶段定位

Phase 3.2 云端任务是兼容本地端增强 JSON，并在教师端/报告页做轻量展示。

核心原则：

```text
上传入口不变
raw JSON 原样保存
增强字段 optional
旧数据继续可用
数据库暂不迁移
```

## 2. 非目标

本阶段不做：

- 不重写 `POST /api/interaction-results`。
- 不新增必需上传 API。
- 不做数据库迁移。
- 不修改 raw JSON 结构。
- 不破坏 Phase 2.9 登录/权限。
- 不修改本地端或树莓派端代码。

## 3. 兼容字段

云端需要兼容以下 Phase 3.2 optional 字段：

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

字段不存在时，旧页面和旧 API 必须正常工作。

## 4. API 设计

### 4.1 上传接口

保持不变：

```text
POST /api/interaction-results
```

要求：

- 旧 JSON 可上传。
- Phase 3.2 enhanced JSON 可上传。
- 新增字段不导致校验失败。
- raw JSON 原样保存新增字段。
- 数据库写入仍只依赖已有核心字段。

### 4.2 detail API

保持现有路由：

```text
GET /api/teacher/results/{result_id}
```

要求：

- 如果 raw JSON 中存在 enhanced fields，detail 返回中必须能读取到。
- 如果当前 detail API 有白名单过滤，需要加入 Phase 3.2 字段或返回 raw。
- 不强制改变已有 API 外形。

### 4.3 recent / classrooms / status API

保持现有行为：

```text
GET /api/teacher/results/recent
GET /api/teacher/classrooms
PATCH /api/teacher/results/{result_id}/status
```

recent 可以继续轻量，不强制返回全部 enhanced fields。

## 5. 数据库设计

Phase 3.2 不做数据库迁移。

继续使用现有核心表：

```text
analysis_results
```

增强字段保存在 raw JSON 中。后续若需要按 `data_confidence` 或评分拆解筛选统计，再考虑 Phase 3.4 数据库扩展。

## 6. 云端展示设计

### /dashboard

如果存在 Phase 3.2 字段，展示“分析可信度/评分解释”区域：

- `analysis_version`
- `quality_metrics.data_confidence`
- `score_breakdown` 五维分数
- `curve_metadata.window_seconds / smoothing`
- `evidence_summary` 证据摘要
- `enhanced_issues` Top 3

字段不存在时降级为旧展示，不报错。

### /teacher/reports

如果存在 `enhanced_issues`，报告详情展示：

- 问题标签
- severity
- reason
- evidence
- suggestion

AI 未配置时不能假装 AI 已生成。规则分析建议可使用 enhanced issues。

### /admin/ingestion

可选展示：

- 视频证据状态
- 标准化视频状态
- 关键帧数量
- data_confidence

如果实现成本高，admin ingestion 只保持兼容也可接受。

## 7. 验证脚本

新增：

```text
scripts/validate_phase3_2_cloud_compat.sh
```

脚本要求：

- 上传 `samples/phase3_2_enhanced_result.json`。
- 检查 HTTP 200。
- 检查 raw 文件存在。
- 检查 raw 文件包含 `"analysis_version": "3.2"`。
- 调用 detail API，检查 enhanced fields。
- 检查 `/dashboard` 可访问。
- 检查 `/teacher/reports` 可访问。

输出至少包含：

```text
PHASE32_CLOUD_UPLOAD_OK=true
PHASE32_RAW_PRESERVED=true
PHASE32_DETAIL_ENHANCED_FIELDS_PRESENT=true
PHASE32_DASHBOARD_OK=true
PHASE32_REPORTS_OK=true
```

## 8. 验收标准

- 旧 JSON 上传成功。
- Enhanced JSON 上传成功。
- Raw JSON 完整保存增强字段。
- Detail API 能返回或读取增强字段。
- Dashboard 能展示增强解释或正常降级。
- Reports 能展示增强问题或正常降级。
- 无数据库迁移。
- API 路由保持不变。
