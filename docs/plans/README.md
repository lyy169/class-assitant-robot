# docs/plans

## 目录作用

`docs/plans/` 用于存放架构设计、跨端接口约定、技术方案、演进计划和重要设计决策文档。

本目录中的文档主要回答以下问题：
- 三端之间如何通信
- JSON 结构如何定义和演进
- 哪些字段是必填、可选或兼容保留
- 某个阶段准备采用什么技术方案
- 接口升级是否属于 breaking change

## 使用规则

- 所有跨端接口约定文档必须存放在 `docs/plans/` 下。
- 跨端接口变更前，必须先更新本目录中的相关文档并记录版本。
- 每份接口文档必须包含：字段说明、示例 JSON、错误码、变更记录、版本号（`schema_version`）。
- 云端接口默认向后兼容；除非文档中明确声明为 breaking change，否则不得随意删除或修改已有字段。
- 本地高性能电脑端输出到云端的 JSON 必须包含 `schema_version` 字段。

## 文件命名规范建议

跨端接口文档建议采用以下命名方式：

- `pi-to-local-xxx.md`
- `local-to-cloud-xxx.md`
- `cross-end-xxx-plan.md`

示例：

- `pi-to-local-keyframe-upload.md`
- `local-to-cloud-interaction-result-schema.md`
- `cross-end-network-and-firewall-plan.md`
- `cloud-data-storage-evolution-plan.md`

## 与 Constitution 的关联说明

本目录是 Constitution 1.3 中“跨端通信铁律”和“接口兼容原则”的直接落点：

- 树莓派到本地电脑只能传关键帧序列
- 本地电脑到云服务器只能传统计结果 JSON
- 所有跨端接口必须在 `docs/plans/` 中有明确文档
- 变更前必须更新文档并记录版本
- 接口应默认保持向后兼容

因此，`docs/plans/` 是跨端协作的基准目录，任何涉及字段、协议、端口、鉴权或调用方式的变化，都必须先在这里落文档。
