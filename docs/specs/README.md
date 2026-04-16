# docs/specs

## 目录作用

`docs/specs/` 用于存放三端详细规格文档，描述各端模块职责、输入输出、行为约束、性能要求和边界条件。

本目录中的文档主要用于明确“每个端内部应该如何工作”，包括但不限于：
- 树莓派端语音与关键帧采集规格
- 本地高性能电脑端接收、推理、统计规格
- 云服务器端接收、存储、查询与仪表盘规格

## 使用规则

- 每次开始某一端的重要开发任务前，应先补齐或阅读对应规格文档。
- 规格文档应描述模块目标、职责、输入输出、异常处理、性能限制和验收标准。
- `docs/specs/` 关注“模块内部规则”，不替代跨端通信文档。
- 若某端行为会影响跨端字段或调用方式，必须同步更新 `docs/plans/` 中的接口文档。

## 文件命名规范建议

建议按“端 + 模块 + 主题”命名：

- `edge-xxx-spec.md`
- `local-xxx-spec.md`
- `cloud-xxx-spec.md`

示例：

- `edge-dialogue-pipeline-spec.md`
- `edge-keyframe-capture-spec.md`
- `local-yolo-interaction-processor-spec.md`
- `local-keyframe-receiver-spec.md`
- `cloud-interaction-ingestion-spec.md`
- `cloud-dashboard-query-spec.md`

## 与 Constitution 的关联说明

本目录对应 Constitution 1.3 中以下要求：

- 三端必须严格遵守模块边界开发
- 每次任务必须明确是哪个端
- 修改前必须阅读相关 Spec 和 Plan 文件
- 树莓派端必须优先保证资源占用与对话流畅性

因此，`docs/specs/` 是各端开发边界和行为约束的正式落点，用于保证实现不偏离项目架构原则。
