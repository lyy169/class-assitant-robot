# 树莓派真机验证准备记录

## 1. 本轮目标

本轮只做真机验证准备，不扩功能，不改采集主线。

目标是补齐一份可执行的真机验证 runbook，便于后续在真实树莓派设备上验证 session 交付链路。

## 2. 当前已准备内容

当前仓库中已经具备以下准备内容：

- session 交付规范文档：
  - `docs/specs/pi-session-delivery-v1.md`
- session 样例目录：
  - `samples/pi-session-delivery-v1/example-classroom/2026-04-20/session-demo/`
- 本轮新增真机验证 runbook：
  - `docs/runbooks/pi-real-device-validation-v1.md`

当前这些内容已经足够支持：

- 明确 session 正式目录结构
- 明确四个最小交付文件
- 明确 metadata 与 transcript 的基本契约
- 指导用户在真机上执行一次最小采集验证

## 3. 当前仓库边界

当前仓库是：

- `video_project_src`

当前访问方式是：

- SSHFS 挂载

在这个仓库内，当前可以确认的是：

- 已有 Pi session 交付规范文档
- 已有样例 session 目录
- 已能补充 runbook 和项目状态记录

在这个仓库内，当前不能声称已完成的是：

- 真正启动树莓派运行时
- 真正执行 `capture_session.py`
- 真正生成真实课堂 session
- 真正观察设备上的 `delivery_status` 演进

原因是当前仓库内并没有可直接执行的 `capture_session.py` 运行时文件。

## 4. 仍需用户执行的真机步骤

以下步骤必须由用户在真实树莓派运行时仓库执行：

1. 找到包含 `capture_session.py` 的树莓派运行时仓库。
2. 执行 `python capture_session.py --help`，确认当前 CLI 参数形式。
3. 启动一次短时采集：

```bash
python capture_session.py start --classroom-id classroom-demo --device-id pi-demo-01
```

4. 采集中执行状态查询：

```bash
python capture_session.py status
```

5. 结束采集：

```bash
python capture_session.py stop
```

6. 检查真实 session 目录下是否存在：
   - `video.mp4`
   - `audio.wav`
   - `metadata.json`
   - `teacher_transcript.json`
7. 打开 `metadata.json`，确认最终至少满足：
   - `status = completed`
   - `delivery_status = ready`
   - `session_ready = true`
8. 检查 `delivery_path` 指向的共享目录中是否也存在完整四文件。

如果实际 CLI 参数与示例不同，应以真机仓库中的 `--help` 输出为准。

## 5. 推荐用户在真机保存的验证证据

建议用户在真机完成验证后，至少保留以下内容：

- `python capture_session.py status` 的终端输出
- 真实 session 目录路径
- 本地 `metadata.json`
- 交付目录中的 `metadata.json`
- 四文件的文件大小信息

这些证据后续可用于确认：

- session 目录是否稳定落盘
- `delivery_status` 是否真的进入 `ready`
- 下游是否可以开始自动消费

## 6. 当前结论

本轮已经完成的是“真机验证准备”而不是“真机验证执行”。

当前状态可以明确表述为：

- runbook 已补齐
- session 契约已有文档和样例
- 真机命令顺序已整理
- 真实设备执行仍需用户在树莓派运行时仓库完成
