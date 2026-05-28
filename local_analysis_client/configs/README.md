# Config Templates

这个目录用于存放未来三端分层配置模板。

当前这些文件仅用于：

- 说明未来配置拆分方向
- 为后续代码适配做准备
- 避免继续把所有配置长期混在单一 `config.yaml` 中

当前运行链路仍以根目录 `config.yaml` 为准。

## 当前模板说明

- `base.yaml`：跨三端共享的默认值模板
- `local-processor.yaml`：本地 YOLO 推理与统计主计算端模板
- `pi-edge.yaml`：树莓派采集、关键帧与上传模板
- `cloud.yaml`：云端接口与存储模板

这些模板当前只用于设计对齐，不代表运行中代码已经按分层配置加载。

## 当前与 `config.yaml` 的映射重点

本地主链路当前已明确依赖以下配置段：

- `paths`：关键帧接收目录、结果输出目录
- `models`：合并模型或兼容双模型路径
- `inference`：推理阈值与输入尺寸
- `statistics`：20 秒窗口与 3x3 区域统计参数
- `cloud`：结果推送地址、开关、超时
- `runtime`：可选的 `source_host` 覆盖值

如果 `runtime.source_host` 未配置，本地处理器会自动回退到当前主机名。
