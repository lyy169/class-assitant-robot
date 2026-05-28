# 树莓派真机验证 Runbook V1

本文用于准备后续在真实树莓派设备上验证 session 交付链路。

当前约束必须先说明清楚：

- 当前访问方式是 SSHFS 挂载
- 当前仓库 `video_project_src` 主要承载规范、样例与云端代码
- 当前仓库内没有可直接执行的 `capture_session.py`
- 因此，本文中的命令是“待用户在真实树莓派运行时仓库执行”的 runbook，不代表已经在本轮实际执行成功

## 1. 目标

本 runbook 只验证一条链路是否真实可用：

- 启动 `capture_session.py`
- 生成一份真实 session
- 观察 `delivery_status` 的变化
- 验证 session 进入 `ready`

本轮不包括：

- 实时对话回归
- 课堂分析
- 云端上传联调
- 大规模系统回归

## 2. 预期前提

执行真机验证前，应满足以下条件：

- 树莓派上存在实际运行时仓库，且仓库内包含 `capture_session.py`
- 树莓派摄像头、麦克风、存储目录可正常访问
- 运行时仓库已经同步当前 session 交付约束
- 预期 session 目录结构仍为：

```text
captures/{classroom_id}/{date}/{session_id}/
  video.mp4
  audio.wav
  metadata.json
  teacher_transcript.json
```

- 如果启用了共享交付目录，还应存在复制后的交付目录，例如：

```text
captures_local_delivery/{classroom_id}/{date}/{session_id}/
  video.mp4
  audio.wav
  metadata.json
  teacher_transcript.json
```

## 3. 如何运行 `capture_session.py`

以下命令必须在真实树莓派运行时仓库执行，不是在当前 SSHFS 文档仓库执行。

### 3.1 进入运行时仓库

```bash
cd /path/to/pi-runtime-repo
```

先确认文件存在：

```bash
ls -l capture_session.py
```

建议先看 CLI 帮助，确认当前参数名：

```bash
python capture_session.py --help
```

### 3.2 启动采集

如果当前 CLI 仍保持 `start / status / stop` 形式，建议先按以下顺序执行：

```bash
python capture_session.py start --classroom-id classroom-demo --device-id pi-demo-01
```

如果实际参数名不同，以 `python capture_session.py --help` 的输出为准。

### 3.3 查看运行状态

```bash
python capture_session.py status
```

建议至少记录以下信息：

- 当前 session 目录
- 当前 `delivery_status`
- 当前 `session_ready`
- 当前 `delivery_path`

### 3.4 停止采集

```bash
python capture_session.py stop
```

停止后应进入收尾与交付阶段。

## 4. 如何生成真实 session

建议按最小流程执行一次短时采集：

1. 启动采集。
2. 保持摄像头和麦克风输入 10 到 30 秒。
3. 执行停止命令。
4. 等待 session 文件全部落盘与共享目录复制完成。

完成后，预期会生成一个真实 session 目录，例如：

```text
captures/classroom-demo/2026-04-20/session-20260420-001/
```

目录中至少应有：

- `video.mp4`
- `audio.wav`
- `metadata.json`
- `teacher_transcript.json`

## 5. 如何观察 `delivery_status` 变化

建议在采集过程中与停止后，重点观察 session 目录中的 `metadata.json`。

### 5.1 找到当前 session 目录

如果 `status` 命令会输出目录路径，直接使用该路径。

如果不会输出，可在采集根目录下按最近修改时间查找：

```bash
find captures -type f -name metadata.json | sort
```

### 5.2 查看 metadata

```bash
cat captures/<classroom_id>/<date>/<session_id>/metadata.json
```

如果系统中有 Python，也可以只读出关键字段：

```bash
python -c "import json,sys; m=json.load(open(sys.argv[1], encoding='utf-8')); print({'status': m.get('status'), 'delivery_status': m.get('delivery_status'), 'session_ready': m.get('session_ready'), 'delivery_path': m.get('delivery_path')})" captures/<classroom_id>/<date>/<session_id>/metadata.json
```

### 5.3 预期状态变化

如果运行时已同步最新交付语义，`delivery_status` 建议按以下过程变化：

- `recording`
- `finalizing`
- `copying`
- `ready`

出现 `failed` 时，应记录 `metadata.json.error`。

## 6. 如何验证 `ready` 状态

只有满足以下条件，才应认为该 session 可以被下游消费：

1. `metadata.json.status` 为 `completed`
2. `metadata.json.delivery_status` 为 `ready`
3. `metadata.json.session_ready` 为 `true`
4. 本地 session 目录存在四个文件
5. 交付目录存在四个文件
6. `metadata.json.delivery_path` 指向实际存在的交付目录

### 6.1 本地目录核对

```bash
ls -lh captures/<classroom_id>/<date>/<session_id>/
```

### 6.2 交付目录核对

```bash
ls -lh captures_local_delivery/<classroom_id>/<date>/<session_id>/
```

如果 `delivery_path` 使用了其他共享目录，以 `metadata.json.delivery_path` 为准。

### 6.3 transcript 可为空但不能缺文件

如果 STT 当前不可用，`teacher_transcript.json` 可以是空数组：

```json
[]
```

但该文件本身仍应存在，且 metadata 中应明确标记 transcript 不可用状态。

## 7. 建议保留的真机验证证据

完成一次真机验证后，建议至少保留以下证据：

- `python capture_session.py status` 输出截图或终端记录
- 真实 session 目录路径
- 本地 `metadata.json`
- 交付目录中的 `metadata.json`
- 四文件的 `ls -lh` 输出
- 如果 transcript 可用，保留 `teacher_transcript.json` 的前几条样例

## 8. 当前 SSHFS 下已能做什么

在当前 `video_project_src` 挂载仓库中，本轮只能完成以下准备工作：

- 补充 session 交付规范文档
- 补充真机验证 runbook
- 检查样例 session 目录结构
- 为后续真机执行准备命令模板

本轮没有实际完成以下事项：

- 在树莓派上启动 `capture_session.py`
- 生成真实视频和音频
- 观察真实 `delivery_status` 变化
- 验证真实 `ready` session

## 9. 最小执行顺序

建议用户在真机上按以下顺序执行：

1. 进入真实树莓派运行时仓库并确认 `capture_session.py` 存在。
2. 执行 `python capture_session.py --help`，确认参数形式。
3. 启动一次短时采集。
4. 运行 `python capture_session.py status` 记录状态。
5. 执行停止命令。
6. 打开 `metadata.json`，确认 `delivery_status` 最终为 `ready`。
7. 检查本地目录和共享交付目录中四文件是否完整。
8. 保存本次 session 路径与 metadata 作为真机验证证据。
