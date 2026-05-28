# 云服务器端当前架构摸底

本文只基于当前 `video_project_src` 中的真实代码、样例数据、runbook 与已做过的本地验证结果编写，不描述理想状态。

当前摸底范围主要参考：

- [cloud_backend/main.py](x:\video_project_src\cloud_backend\main.py)
- [cloud_backend/schemas_v11.py](x:\video_project_src\cloud_backend\schemas_v11.py)
- [cloud_backend/storage.py](x:\video_project_src\cloud_backend\storage.py)
- [cloud_backend/dashboard_v11.py](x:\video_project_src\cloud_backend\dashboard_v11.py)
- [cloud_backend/sample_data/latest_demo_result.json](x:\video_project_src\cloud_backend\sample_data\latest_demo_result.json)
- [cloud_backend/RUNBOOK.md](x:\video_project_src\cloud_backend\RUNBOOK.md)
- [cloud-results-dashboard-runbook.md](x:\video_project_src\docs\runbooks\cloud-results-dashboard-runbook.md)
- [validate_cloud_results_center.sh](x:\video_project_src\scripts\validate_cloud_results_center.sh)

## 1. 当前职责定位

### 当前正式主线职责

云服务器端当前正式主线在 `cloud_backend/`，已经真实承担：

- 接收本地端 JSON
- 协议校验
- 文件存储
- 基于文件的轻量摘要索引
- latest / recent 查询接口
- dashboard 展示

对应主线入口见 [main.py](x:\video_project_src\cloud_backend\main.py:72)。

### 当前未完成或未形成正式主线的职责

当前未形成正式主线，或者代码里没有真正落地的部分：

- detail 查询接口
- trend 聚合接口
- 数据库抽象层
- 视频留档与 dashboard 联动
- 真实本地端上传后的端到端已验通链路记录

### 当前保留兼容但不是主线的内容

- `_extract_payload_dict()` 仍兼容直接 JSON 或带 `payload` 外层 envelope 的提交方式，见 [main.py](x:\video_project_src\cloud_backend\main.py:43)
- 旧 `schemas.py` 文件仍在仓库里，但主入口已经改用 [schemas_v11.py](x:\video_project_src\cloud_backend\schemas_v11.py:1)
- 旧 Flask / MP4 / 视频浏览能力仍在旧系统里保留，但不在当前云端正式主接口主线上

## 2. 当前已完成能力清单

### 能力 1：健康检查

- 能力名称：服务健康检查
- 对应代码文件：[main.py](x:\video_project_src\cloud_backend\main.py:72)
- 入口脚本或路由：`GET /health`
- 输入：无
- 输出：`{"status": "ok"}`
- 当前验证级别：结构验证 + 本地测试调用已验证

### 能力 2：V1.1 协议校验

- 能力名称：课堂反馈 JSON `v1.1` 校验
- 对应代码文件：[schemas_v11.py](x:\video_project_src\cloud_backend\schemas_v11.py:1)
- 入口脚本或路由：`POST /api/interaction-results`
- 输入：课堂反馈 JSON `v1.1`
- 输出：Pydantic 校验通过后进入存储；不通过则抛校验异常
- 当前验证级别：结构验证已完成；真实本地端 JSON 上传尚未在当前文档范围内看到已验通记录

### 能力 3：正式接收接口

- 能力名称：课堂反馈结果接收
- 对应代码文件：[main.py](x:\video_project_src\cloud_backend\main.py:133)
- 入口脚本或路由：`POST /api/interaction-results`
- 输入：本地端发送的 `v1.1` JSON，支持直接 body 或 `payload` envelope
- 输出：统一 `ApiResponse`，包含 `success`、`request_id`、`saved_path`
- 当前验证级别：代码路径已完成；当前文档中未看到真实本地端 JSON 对该接口的已验通记录

### 能力 4：文件存储

- 能力名称：原始分析 JSON 按日期落盘
- 对应代码文件：[storage.py](x:\video_project_src\cloud_backend\storage.py:18)
- 入口脚本或路由：由 `POST /api/interaction-results` 调用 `repository.save()`
- 输入：已通过校验的完整 payload
- 输出：`cloud_backend/data/raw/YYYY-MM-DD/<analysis_id>.json`
- 当前验证级别：结构验证已完成；真实本地端上传写盘未见本轮已验通证据

### 能力 5：latest 查询

- 能力名称：最近一条结果查询
- 对应代码文件：[main.py](x:\video_project_src\cloud_backend\main.py:78)、[storage.py](x:\video_project_src\cloud_backend\storage.py:33)
- 入口脚本或路由：`GET /api/latest-interaction-result`
- 输入：可选 `classroom_id`
- 输出：`success`、`source_kind`、`source_path`、`result`
- 当前验证级别：sample/fallback 已验通

### 能力 6：recent 查询

- 能力名称：最近 N 条结果查询
- 对应代码文件：[main.py](x:\video_project_src\cloud_backend\main.py:90)、[storage.py](x:\video_project_src\cloud_backend\storage.py:45)
- 入口脚本或路由：`GET /api/recent-interaction-results`
- 输入：`limit`，可选 `classroom_id`
- 输出：`results[]`，每条包含 `source_kind`、`source_path`、`summary`、`result`
- 当前验证级别：sample/fallback 已验通

### 能力 7：按课堂筛选

- 能力名称：按 `classroom_id` 过滤 recent / latest
- 对应代码文件：[main.py](x:\video_project_src\cloud_backend\main.py:79)、[main.py](x:\video_project_src\cloud_backend\main.py:93)、[storage.py](x:\video_project_src\cloud_backend\storage.py:52)
- 入口脚本或路由：
  - `GET /api/latest-interaction-result?classroom_id=...`
  - `GET /api/recent-interaction-results?classroom_id=...`
  - `GET /dashboard?classroom_id=...`
- 输入：`classroom_id`
- 输出：仅返回匹配 classroom 的最新或 recent 结果
- 当前验证级别：sample/fallback 已验通

### 能力 8：dashboard 展示

- 能力名称：教师结果中心页面
- 对应代码文件：[main.py](x:\video_project_src\cloud_backend\main.py:114)、[dashboard_v11.py](x:\video_project_src\cloud_backend\dashboard_v11.py:20)
- 入口脚本或路由：`GET /dashboard`
- 输入：可选 `classroom_id`、`limit`
- 输出：HTML 页面
- 当前验证级别：sample/fallback 已验通

## 3. 当前正式协议与接口

### 当前正式 schema 文件

当前正式 schema 文件是：

- [schemas_v11.py](x:\video_project_src\cloud_backend\schemas_v11.py:1)

该文件已明确：

- `schema_version` 必须为 `v1.1`
- `teacher.question_events` 使用 `start_sec / end_sec`
- `timeline.attention_curve / heat_curve / activity_curve` 长度必须一致
- 比例字段为 `0-1`
- 评分字段为 `0-100`

### 当前正式入口路由

当前正式入口路由在 [main.py](x:\video_project_src\cloud_backend\main.py:72)：

- `GET /health`
- `POST /api/interaction-results`
- `GET /api/latest-interaction-result`
- `GET /api/recent-interaction-results`
- `GET /dashboard`

### V1.1 对齐程度

当前对齐情况是：

- 接收校验：已改到 `v1.1`
- sample 数据：已改到 `v1.1`
- recent / latest 摘要提取：已改到 `v1.1`
- dashboard 展示：已围绕 `summary / teacher / students / timeline` 展示
- 真实本地端实际上传并消费：当前文档范围内没有已验通证据

### 仍保留但不是主线的旧 schema / 旧接口

- [schemas.py](x:\video_project_src\cloud_backend\schemas.py:1) 仍在仓库，但当前主入口不再引用
- 路由命名仍保留 `interaction-results` 这一旧语义，但 payload 实际已切到课堂反馈 `v1.1`

### 本地端当前应 POST 到哪个正式接口

本地端当前应 POST 到：

- `POST /api/interaction-results`

这也是当前唯一已实现的正式接收接口。

## 4. 当前存储与索引

### 当前如何保存分析 JSON

当前由 [storage.py](x:\video_project_src\cloud_backend\storage.py:18) 保存：

- 目录：`cloud_backend/data/raw/YYYY-MM-DD/`
- 文件名：`<analysis_id>.json`

### 当前是否按 analysis_id / classroom_id / recorded_at 查询

当前状态：

- `analysis_id`：用于文件命名，但没有 detail 查询接口
- `classroom_id`：已有过滤能力
- `recorded_at`：被读取到摘要中，但没有独立查询接口
- `generated_at`：用于 recent 排序

### recent / list / detail / trend 的数据来源

- latest：来自文件仓储扫描，优先 raw，再 fallback sample
- recent/list：来自文件仓储扫描，优先 raw，再 fallback sample
- detail：未实现
- trend：未实现

### 当前是文件仓储还是已有数据库抽象

当前是纯文件仓储：

- 仓储实现：[storage.py](x:\video_project_src\cloud_backend\storage.py:12)
- 没有数据库抽象层
- 没有 SQLite / PostgreSQL 落地代码

### 哪些部分仍是 sample_data / fallback

当前 fallback 机制真实存在：

- sample 数据目录：[latest_demo_result.json](x:\video_project_src\cloud_backend\sample_data\latest_demo_result.json:1)
- recent / latest / dashboard 都会在 raw 不存在时回退到 sample
- API 中还会返回 `source_kind`

## 5. 当前 dashboard 展示边界

### 当前围绕 V1.1 已接入的展示字段

参考 [dashboard_v11.py](x:\video_project_src\cloud_backend\dashboard_v11.py:20)：

- `summary`
  - `feedback_score`
  - `attention_score`
  - `response_score`
  - `teacher_question_count`
  - `avg_attention_ratio`
  - `response_success_rate`
  - `summary_text`
- `teacher.question_events`
- `teacher.stage_distribution`
- `students.estimated_student_count`
- `students.hand_raise_event_count`
- `students.zones`
- `timeline.attention_curve`
- `timeline.heat_curve`
- `timeline.activity_curve`

### 5.1 样例演示已通过的字段

根据 sample 数据和本地测试调用，已用 sample/fallback 验通：

- `summary.*`
- `teacher.question_events`
- `teacher.stage_distribution`
- `students.estimated_student_count`
- `students.hand_raise_event_count`
- `students.zones`
- `timeline.attention_curve`
- `timeline.heat_curve`
- `timeline.activity_curve`

### 5.2 真实上传结果已可消费的字段

当前文档范围内无法确认“真实本地端上传结果已可消费”的字段列表。

更准确地说：

- 代码已经准备好消费上述字段
- 但目前没有看到真实本地端上传并被 dashboard 展示的已验证记录

### 5.3 尚未完成验证的字段

以下不应说成“已验通”：

- 真实本地端上传后的 `summary.*`
- 真实本地端上传后的 `teacher.question_events`
- 真实本地端上传后的 `students.zones`
- 真实本地端上传后的 `timeline.*`
- raw 文件存在时 recent / latest / dashboard 是否完整读取真实数据

## 6. 与本地端的对齐现状

### 当前是否已经准备好直接接收本地端 V1.1 JSON

是，当前代码已经准备好直接接收本地端 `v1.1` JSON。

依据：

- 正式 schema 已是 `v1.1`
- 主入口已引用 [schemas_v11.py](x:\video_project_src\cloud_backend\schemas_v11.py:1)
- 存储和 dashboard 已围绕 `v1.1` 顶层结构提取字段

### 当前仍存在的协议风险

当前仍有这些协议风险：

- 路由名仍叫 `interaction-results`，而 payload 其实已经是 classroom feedback `v1.1`
- 旧 [schemas.py](x:\video_project_src\cloud_backend\schemas.py:1) 仍在仓库，可能造成误用
- runbook 有部分描述仍保留旧“interaction”措辞
- 尚无真实本地端 `v1.1` JSON 上传后的端到端验通证据

### 当前接口命名是否存在 interaction / classroom analysis 混用问题

存在。

具体表现：

- 路由：`/api/interaction-results`
- schema / 页面含义：已变成 classroom feedback `v1.1`
- dashboard 标题仍是“Teacher Results Center”，不再只是 interaction 统计

### 是否建议下一步统一命名，还是先保持现状打通链路

从当前真实状态看，更合理的是：

- 先保持现有接口命名不动
- 先把真实本地端 `v1.1` JSON 直连打通
- 等真实链路稳定后，再决定是否统一命名

原因是当前最缺的不是重命名，而是真实上传验证。

## 7. 当前真实验证边界

### 已用 sample / fallback 验通的部分

已通过本地 `TestClient` 方式完成 sample/fallback 验证的部分：

- `GET /api/latest-interaction-result`
- `GET /api/recent-interaction-results`
- `GET /api/recent-interaction-results?classroom_id=classroom_101`
- `GET /dashboard?classroom_id=classroom_101`
- dashboard 对 `summary / teacher / students / timeline` 的基础展示

### 已用真实本地端 JSON 验通的部分

当前文档范围内，没有可引用的“真实本地端 JSON 已验通”记录。

也就是说：

- 不能把真实本地端上传说成已经验通
- 不能把真实 raw 数据消费说成已经验通

### 尚未验证的部分

- 本地端真实 `v1.1` JSON 通过 `POST /api/interaction-results` 的上传过程
- 上传后 raw 文件是否按预期落在 `cloud_backend/data/raw/YYYY-MM-DD/<analysis_id>.json`
- 上传后 recent / latest 是否优先读取 raw 而不是 sample
- 上传后 dashboard 是否完整消费真实字段

## 8. 当前最真实的主链路

当前真正已打通、并且可以明确说出来的主链路是：

sample / fallback JSON  
-> `GET /api/latest-interaction-result` / `GET /api/recent-interaction-results`  
-> 文件仓储摘要提取  
-> `GET /dashboard`  
-> 教师结果中心页面展示

如果按“接收 -> 校验 -> 存储 -> 查询 -> 展示”完整链路来写，当前最真实的状态是：

- 接收：代码已完成，但真实本地端上传未见已验通记录
- 校验：`schemas_v11.py` 已完成
- 存储：`storage.py` 已完成文件写盘逻辑
- 查询：latest / recent 已完成
- 展示：dashboard 已完成 sample/fallback 级别展示

## 9. 当前最应该保持稳定的部分

### 现在最不应该再乱动的接口和数据结构

- `POST /api/interaction-results`
- `GET /api/latest-interaction-result`
- `GET /api/recent-interaction-results`
- `GET /dashboard`
- [schemas_v11.py](x:\video_project_src\cloud_backend\schemas_v11.py:1) 中的 `v1.1` 协议结构
- [storage.py](x:\video_project_src\cloud_backend\storage.py:18) 中以 `analysis_id` 命名的写盘方式

### 可暂时保留但不该继续扩展的旧兼容部分

- `_extract_payload_dict()` 的 envelope 兼容
- 旧 `schemas.py`
- 旧 interaction 命名语义
- 旧 Flask / legacy 相关能力

### 云服务器端下一阶段最合理的职责边界

按当前真实现状，云服务器端下一阶段最合理的职责边界是：

- 稳定接收本地端 `v1.1` JSON
- 稳定文件落盘
- 稳定 latest / recent 查询
- 稳定 dashboard 展示

而不是：

- 大规模改命名
- 强行合并旧 Flask
- 继续扩很多新字段

## 10. 最终结论

云服务器端当前真正稳定的主线是：

- `cloud_backend/`
- `v1.1` schema 校验
- 文件仓储
- latest / recent 查询
- 基于 sample/fallback 的 dashboard 展示

云服务器端当前已经准备好接收的数据是：

- 符合 [schemas_v11.py](x:\video_project_src\cloud_backend\schemas_v11.py:1) 的课堂反馈 JSON `v1.1`

当前是否需要重构：

- 不需要大重构
- 更接近“正式接口和正式协议已经定下来，只差真实本地端把这份 JSON 发上来并验证全链路”

下一步最关键的不是展示增强，而是：

- 本地端对接真实 `v1.1` JSON
- 验证 `POST /api/interaction-results` -> raw 文件 -> recent/latest -> dashboard 的真实链路

