## 2. `v2-phase2-result-workbench-tasks.md`

```md
# V2 Phase 2 Tasks：结果工作台与课堂筛选增强

## 0. 执行原则

本轮开发必须遵守：

- 不推翻 Phase 1
- 不重构已跑通链路
- 小步修改，小步验证
- 每完成一个后端接口都要 curl 验证
- 每完成一个前端功能都要浏览器验证
- 所有变更写入状态文档

## 1. 代码现状探查

### Task 1.1 检查后端目录结构

目标：

确认当前 backend 入口、API 路由、数据库访问代码位置。

需要输出：

- 后端入口文件路径
- teacher API 所在文件
- analysis_results 查询逻辑位置
- PostgreSQL 连接逻辑位置

验收：

- 在终端输出相关文件路径
- 不修改业务代码

---

### Task 1.2 检查 analysis_results 表结构

目标：

确认当前字段。

需要执行：

- 查看建表 SQL 或 ORM model
- 使用 psql 查询字段
- 判断是否已有 classroom_id / status / created_at / updated_at

验收：

- 明确是否需要迁移
- 记录现有字段

---

## 2. 数据库增强

### Task 2.1 添加兼容型字段

目标：

为 analysis_results 增加 Phase 2 字段。

字段：

- classroom_id
- classroom_name
- lesson_title
- status
- updated_at

要求：

- 使用 IF NOT EXISTS 或等价兼容方式
- 不破坏已有数据
- status 默认 raw
- updated_at 可为空或默认当前时间

验收：

- 数据库字段存在
- 老数据仍可查询
- Phase 1 数据不丢失

---

### Task 2.2 上传入库逻辑补充字段

目标：

上传新分析结果时尽量写入 classroom 信息。

要求：

- 如果 raw JSON 中有 classroom_id，则入库
- 如果 raw JSON 中有 classroom_name，则入库
- 如果 raw JSON 中有 lesson_title，则入库
- 缺失时允许为空或 unknown
- status 默认 raw

验收：

- 新上传数据包含 status=raw
- classroom 字段缺失时接口不报错

---

## 3. 后端 API 开发

### Task 3.1 增强 recent 接口

接口：

```http
GET /api/teacher/results/recent

新增 query 参数：

limit
classroom_id
status

要求：

limit 默认 10
limit 最大 100
按 created_at DESC
支持课堂筛选
支持状态筛选
保持 fallback_to_sample 字段

验收命令示例：

curl "http://localhost:8000/api/teacher/results/recent?limit=5"
curl "http://localhost:8000/api/teacher/results/recent?classroom_id=101"
curl "http://localhost:8000/api/teacher/results/recent?status=raw"
Task 3.2 新增 classrooms 接口

接口：

GET /api/teacher/classrooms

要求：

从 analysis_results 聚合
返回 classroom_id、classroom_name、result_count、latest_result_at
unknown 课堂允许存在
按 latest_result_at DESC

验收命令：

curl "http://localhost:8000/api/teacher/classrooms"
Task 3.3 增强结果详情接口

接口：

GET /api/teacher/results/{result_id}

要求：

返回完整单条结果
包含 classroom 信息
包含 raw_path
包含 score / events / summary
不存在返回 404
不使用 sample fallback

验收命令：

curl "http://localhost:8000/api/teacher/results/cls_20260417_101_001"
curl -i "http://localhost:8000/api/teacher/results/not_exists"
Task 3.4 新增状态更新接口

接口：

PATCH /api/teacher/results/{result_id}/status

请求体：

{
  "status": "reviewed"
}

要求：

只允许 raw / reviewed / archived
非法 status 返回 400
不存在 result_id 返回 404
更新 updated_at
返回更新后的摘要

验收命令：

curl -X PATCH "http://localhost:8000/api/teacher/results/cls_20260417_101_001/status" \
  -H "Content-Type: application/json" \
  -d '{"status":"reviewed"}'

curl -i -X PATCH "http://localhost:8000/api/teacher/results/cls_20260417_101_001/status" \
  -H "Content-Type: application/json" \
  -d '{"status":"bad_status"}'
4. 前端开发
Task 4.1 定位 dashboard 页面

目标：

找到 dashboard 页面源码和 API 请求代码。

验收：

确认 dashboard 文件路径
确认 recent API 调用位置
Task 4.2 增加筛选器

目标：

dashboard 顶部增加：

课堂下拉框
状态下拉框
limit 选择器
刷新按钮

要求：

页面加载时请求 classrooms
课堂选择变化后重新请求 recent
状态变化后重新请求 recent
limit 变化后重新请求 recent

验收：

浏览器中可以看到筛选器
操作筛选器会触发数据刷新
Task 4.3 改造结果列表

目标：

结果列表显示 Phase 2 字段。

显示：

result_id
classroom
lesson_title
score
status
created_at
查看详情
标记 reviewed
归档

验收：

列表显示真实数据库结果
status 可见
classroom 可见
Task 4.4 增加详情面板

目标：

点击查看详情后展示完整结果。

要求：

调用 detail API
显示 summary、score、events、raw_path
详情加载失败时显示错误

验收：

点击结果可展示详情
不刷新页面
不影响列表筛选
Task 4.5 接入状态更新

目标：

reviewed / archived 按钮可更新状态。

要求：

调用 PATCH status API
成功后刷新列表
如果当前详情是该 result，也刷新详情

验收：

点击 reviewed 后状态变 reviewed
点击 archived 后状态变 archived
页面刷新后状态保持
5. 测试与验证
Task 5.1 后端接口回归

必须验证：

curl "http://localhost:8000/api/teacher/results/recent"
curl "http://localhost:8000/api/teacher/results/recent?limit=5"
curl "http://localhost:8000/api/teacher/classrooms"
curl "http://localhost:8000/api/teacher/results/cls_20260417_101_001"
Task 5.2 上传链路回归

必须验证：

POST 上传接口返回 200
raw JSON 仍落盘
PostgreSQL 仍入库
recent 能查到新结果
dashboard 能看到新结果
Task 5.3 前端浏览器验证

必须验证：

dashboard 页面 200
显示结果列表
筛选课堂可用
筛选状态可用
limit 可用
详情可用
status 更新可用
6. 文档更新
Task 6.1 更新项目状态文档

更新文件：

/root/video_project_src/docs/project-status/v2-phase2-result-workbench.md

内容包括：

本轮目标
修改文件列表
数据库字段变更
新增接口
curl 验证结果
dashboard 验证结果
已知问题
下一轮建议
7. 完成定义

Phase 2 完成标准：

后端 4 个核心能力完成
前端 dashboard 可作为结果中心使用
Phase 1 回归通过
文档已更新
没有 sample fallback 污染真实结果展示