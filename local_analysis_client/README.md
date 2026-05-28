# PI-Assistant1

## 一句话目标

本项目当前面向“课堂教育辅助机器人”的三端协作架构，重点保留并推进课堂互动分析链路：

- 树莓派端负责语音唤醒、语音对话、语音命令触发录像、关键帧采集与 MP4 上传
- 本地电脑端负责 YOLO 推理、课堂互动统计、结果生成
- 云服务器端负责 `video_project` 中的新接口部分

## 当前项目状态

当前第一优先级不是继续堆叠新功能，而是完成 Git 与工程规范化整理，建立三端长期协作所需的安全基线。

当前本地端承担的正式角色是：

- 课堂互动分析主计算端
- 关键帧接收端
- YOLO 推理与统计执行端
- 结果 JSON 生成与推送端

## 三端职责

### 1. 树莓派端（Edge / 本体）

正式保留能力：

- 语音唤醒
- 语音对话
- 语音命令触发录像
- 关键帧采集
- MP4 上传

当前仓库现状：

- 目录已预留：`pi-edge/`
- 代码主线尚未在当前工作树完成归位

### 2. 本地电脑端（Processor）

正式保留能力：

- YOLO 推理
- 课堂互动统计
- 结构化结果生成

当前仓库现状：

- 主链路代码已存在并可作为当前最核心资产保留
- 核心文件仍位于仓库根目录，后续将逐步归位到 `local-processor/`

### 3. 云服务器端（Dashboard / API）

正式保留能力：

- `video_project` 中的新接口部分

不再作为主线继续推进的旧能力：

- 旧 Flask 视频/登录/历史页面主线

当前仓库现状：

- 目录已预留：`cloud-dashboard/`
- 当前工作树未包含完整云端主线代码

## 当前正式保留的能力边界

### 已有

- 本地关键帧接收接口
- 本地 YOLO 互动统计链路
- 本地结构化 JSON 输出
- 本地到云端的结果推送能力
- Spec-Kit 文档骨架

### 规划中

- 树莓派端代码正式归位与规范化
- 云端新接口与数据展示部分归位
- 配置分层、目录归位、跨端联调稳定化

### legacy / 待整理

- 远程 `origin/main` 中与旧语音机器人主线相关的历史资产
- 当前根目录中的实验脚本与临时文件
- 尚未进入三端正式目录结构的旧文件

## 文档入口

- Constitution 锚点文件：`constitution.md`
- 变更记录：`docs/changes/`
- 规格文档：`docs/specs/`
- 计划与接口约定：`docs/plans/`
- 当前基线说明：`docs/project-status/2026-04-baseline.md`
- 文档可信度清单：`docs/project-status/document-trust-status.md`
- 运行产物清单：`docs/project-status/runtime-artifact-inventory.md`
- 本地 legacy 资产清单：`docs/project-status/local-legacy-asset-status.md`
- 本地归位任务清单：`docs/tasks/local-processor-normalization.md`
- 本地主链路运行手册：`docs/runbooks/local-analysis-runbook.md`

## 当前工作原则

当前阶段默认遵循以下原则：

1. 优先修复 Git 可追踪性与主线混乱问题
2. 优先补齐项目入口文档与现状文档
3. 优先做可回滚整理，不做激进重构
4. 不直接在 `main` 上做整理
5. 不强推 `origin/main`

## 当前仓库中的临时资产说明

以下目录或文件当前主要属于运行产物、训练产物或联调样本，不应视为三端正式目录结构的一部分：

- `processed_results/`
- `received_keyframes/`
- `runs/`
- `datasets/`
- 根目录 `tmp_*.log`、`test.json`

这类内容当前以“保留现场、避免误删”为原则处理：

- 先通过 `.gitignore` 和文档治理
- 后续确认后再决定归档、迁移或清理
