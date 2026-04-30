# V2 Phase 2 Spec：结果工作台与课堂筛选增强

## 0. 背景

Phase 1 已完成闭环：

- 分析结果上传接口可用
- raw JSON 可落盘
- PostgreSQL 可入库
- teacher API 可查询 detail / trends / recent
- dashboard 可展示最近结果
- fallback_to_sample=false 时可展示真实结果

Phase 2 不重构 Phase 1，不替换已有数据链路，而是在现有闭环上增强结果管理能力。

## 1. Phase 2 目标

建设一个“结果工作台”，让教师可以围绕课堂、时间、结果状态查看分析结果。

核心目标：

1. 支持按课堂筛选分析结果
2. 支持最近 N 条结果分页/限制查询
3. 支持结果详情中心化展示
4. 支持 dashboard 从“简单展示”升级为“结果中心”
5. 增加基础状态字段，为后续审核、归档、标注做准备
6. 保持 Phase 1 所有接口兼容

## 2. 非目标

Phase 2 不做以下内容：

- 不做真实视频 AI 推理
- 不做用户登录与权限系统
- 不做复杂 RBAC
- 不做前端大规模重构
- 不删除 Phase 1 接口
- 不改变 raw JSON 原始存储格式
- 不引入新的数据库替代 PostgreSQL

## 3. 数据模型增强

当前表：`analysis_results`

需要检查现有字段，若字段不存在，则添加迁移或兼容逻辑。

建议新增字段：

| 字段 | 类型 | 说明 |
|---|---|---|
| classroom_id | TEXT / VARCHAR | 课堂 ID |
| classroom_name | TEXT / VARCHAR | 课堂名称 |
| lesson_title | TEXT / VARCHAR | 课程标题 |
| status | TEXT / VARCHAR | 结果状态 |
| created_at | TIMESTAMP | 创建时间 |
| updated_at | TIMESTAMP | 更新时间 |

status 允许值：

- `raw`
- `reviewed`
- `archived`

默认值：

```text
status = raw

如果历史数据缺少 classroom_id，则允许为空，但 API 不应报错。

4. 后端接口需求
4.1 最近结果接口增强

接口：

GET /api/teacher/results/recent

查询参数：

参数	必填	默认值	说明
limit	否	10	返回最近 N 条
classroom_id	否	无	按课堂筛选
status	否	无	按状态筛选

要求：

按 created_at DESC 排序
limit 最大不超过 100
classroom_id 为空时返回所有课堂
status 为空时返回所有状态
保持原有返回结构兼容
返回字段中增加 classroom_id、classroom_name、lesson_title、status

返回示例：

{
  "success": true,
  "fallback_to_sample": false,
  "items": [
    {
      "result_id": "cls_20260417_101_001",
      "classroom_id": "101",
      "classroom_name": "Classroom 101",
      "lesson_title": "Demo Lesson",
      "status": "raw",
      "score": 87,
      "created_at": "2026-04-28T10:00:00Z"
    }
  ]
}
4.2 结果详情接口增强

接口：

GET /api/teacher/results/{result_id}

要求：

返回单条完整结果
包含 summary、score、events、raw_path、classroom 信息
若 result_id 不存在，返回 404
不存在时不能 fallback 到 sample
4.3 课堂列表接口

新增接口：

GET /api/teacher/classrooms

用途：

前端 dashboard 筛选器使用。

返回示例：

{
  "success": true,
  "items": [
    {
      "classroom_id": "101",
      "classroom_name": "Classroom 101",
      "result_count": 12,
      "latest_result_at": "2026-04-28T10:00:00Z"
    }
  ]
}

要求：

从 analysis_results 聚合生成
不需要新增 classrooms 表
classroom_id 为空的数据可以归入 unknown
按 latest_result_at DESC 排序
4.4 结果状态更新接口

新增接口：

PATCH /api/teacher/results/{result_id}/status

请求体：

{
  "status": "reviewed"
}

要求：

status 只能是 raw / reviewed / archived
result_id 不存在返回 404
status 非法返回 400
更新 updated_at
返回更新后的结果摘要
5. 前端 dashboard 需求

当前 dashboard 已可显示 Phase 1 结果。

Phase 2 需要增强为结果中心页面。

5.1 顶部筛选区

需要包含：

课堂筛选下拉框
状态筛选下拉框
limit 选择器：10 / 20 / 50
刷新按钮
5.2 结果列表区

每条结果显示：

result_id
classroom_name / classroom_id
lesson_title
score
status
created_at
查看详情按钮
标记 reviewed 按钮
归档 archived 按钮
5.3 详情区

点击查看详情后，在页面右侧或下方展示：

result_id
classroom 信息
score
summary
events / issues
raw_path
created_at
updated_at
5.4 空状态

当筛选结果为空时显示：

暂无符合条件的分析结果
5.5 错误状态

接口失败时显示：

加载结果失败，请检查后端服务
6. 兼容性要求
Phase 1 已验证的上传接口必须继续通过
Phase 1 recent 接口必须继续返回真实数据
fallback_to_sample=false 的逻辑不能破坏
dashboard 不能因为旧数据缺少 classroom 字段而崩溃
raw 文件路径仍然可展示
7. 验收标准
后端验收
GET /api/teacher/results/recent?limit=5 返回最多 5 条
GET /api/teacher/results/recent?classroom_id=101 只返回课堂 101
GET /api/teacher/classrooms 返回聚合课堂列表
GET /api/teacher/results/{result_id} 返回详情
PATCH /api/teacher/results/{result_id}/status 可更新状态
非法 status 返回 400
不存在 result_id 返回 404
前端验收
dashboard 页面显示筛选区
可以按课堂筛选
可以按状态筛选
可以切换 limit
点击结果后显示详情
可以将结果标记为 reviewed
可以将结果归档为 archived
页面刷新后状态保持
回归验收
Phase 1 上传接口仍返回 200
PostgreSQL 仍写入 analysis_results
raw JSON 仍落盘
teacher recent 仍能返回真实数据
fallback_to_sample=false