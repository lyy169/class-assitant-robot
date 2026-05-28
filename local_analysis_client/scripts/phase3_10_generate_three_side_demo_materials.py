from __future__ import annotations

import argparse
from pathlib import Path


DEFAULT_OUTPUT_DIR = Path(r"C:\Users\lyy\Desktop\gradu\competition_materials")


THREE_SIDE_WORKFLOW = """# 智能课堂行为分析与教学反馈平台三端最终流程

## 1. 树莓派端：课堂采集入口

树莓派端在最终参赛演示中的职责是展示系统的前端采集入口能力：

- 语音唤醒：通过唤醒词激活课堂采集终端。
- 语音指令启动录像：教师或演示人员通过语音指令开始录像。
- 生成课堂视频或采集素材：形成可交付给本地分析端的课堂视频、关键帧或会话素材。

树莓派端证明系统具备低成本边缘采集入口，但不承担最终 SAV 样本的数据来源说明。

## 2. 本地分析端：课堂行为识别与分析

本地分析端负责课堂行为分析主链路：

- 接收或导入课堂视频。
- 执行 YOLO 行为识别与课堂分析。
- 生成 V1.1 分析 JSON。
- 通过 HTTP multipart/form-data 自动上传视频 + JSON 到云端 `/api/interaction-results/with-video`。

Phase 3.6b 已验证本地端不需要手动复制视频到云服务器目录，可以直接把完整课堂视频和分析 JSON 自动发送到云端。

## 3. 云服务器端：数据接收、展示与教学反馈

云服务器端负责教学平台能力：

- 接收本地端上传的视频和 JSON。
- 保存视频到云端 `/uploads` 静态播放目录。
- raw JSON 落盘。
- PostgreSQL 入库。
- 教师端 dashboard 同屏展示课堂视频和分析结果。
- 管理端查看数据接入状态。
- 报告中心展示教学反馈和复盘建议。

## 4. 最终展示数据分工

- `phase37_full_classroom_sav_20200908_17` 是最终完整课堂 dashboard 样本。
- 该样本来自 SAV 外部公开课堂视频，不是树莓派采集，不是自采。
- SAV-50 是外部真实课堂切片验证集，用于支撑算法可信度。
- SAV-50 不是单堂完整课堂 dashboard 主样本，50 个切片不宣称完整覆盖 SAV 15 类动作。
"""


PI_DEMO_BOUNDARY = """# 树莓派端演示边界说明

## 演示角色

树莓派端用于展示系统的采集入口能力，而不是最终 SAV 样本的数据来源。

现场建议演示：

1. 展示语音唤醒。
2. 展示语音指令开始录像。
3. 展示录像文件或采集素材生成。
4. 展示该视频或会话素材可以进入本地分析端流程。
5. 如果现场环境不适合真实课堂录制，则使用短样例证明采集功能，用 SAV 完整课堂样本证明真实课堂分析链路。

## 不应混淆的边界

- 当前最终展示的完整课堂样本来自 SAV 外部公开数据，不是树莓派采集。
- 当前最终展示的完整课堂样本不是项目自采数据。
- 语音触发和录像能力由树莓派端演示证明。
- 完整课堂分析能力由 SAV 外部真实课堂样本展示。
- SAV-50 用于外部验证，不作为课堂 dashboard 主流程。
- 不夸大算法精度，不宣称完整覆盖 SAV 15 类动作。

## 推荐演示顺序

先演示树莓派端语音唤醒和启动录像，说明系统具备边缘采集入口；再切换到本地分析端说明视频如何进入行为识别与 V1.1 JSON 生成；最后打开云端 dashboard 展示 `phase37_full_classroom_sav_20200908_17` 的完整课堂视频和分析结果。
"""


DATA_SOURCE_STATEMENT = """# 比赛数据来源和三端闭环说明

## 数据来源口径

- `phase37_full_classroom_sav_20200908_17` 是最终完整课堂 dashboard 样本。
- 该样本来自 SAV 外部公开课堂视频。
- 该样本不是树莓派采集，不是自采。
- 树莓派端演示的是系统采集入口能力，不承担 SAV 样本来源说明。
- SAV-50 是外部真实课堂切片验证集，不是完整课堂 dashboard 主样本。
- 50 个 SAV-50 切片不宣称完整覆盖 SAV 15 类动作。

## 可直接放入比赛文档的说明

本系统采用树莓派端、本地分析端和云端教师平台的三端架构。树莓派端负责语音唤醒、语音指令启动录像和课堂采集入口展示，证明系统具备低成本边缘采集能力；本地分析端负责接收或导入课堂视频，执行行为识别与课堂分析，生成 V1.1 分析 JSON，并通过 HTTP multipart 自动上传视频和 JSON；云端负责接收、存储、PostgreSQL 入库，并在教师 dashboard 中同屏展示课堂视频、行为曲线和教学反馈。最终完整课堂 dashboard 样本 `phase37_full_classroom_sav_20200908_17` 来自 SAV 外部公开课堂视频，不是树莓派采集或自采数据；SAV-50 仅作为外部真实课堂切片验证集，用于支撑举手、站立等核心行为的可信度说明。

## 演示视频建议

演示视频中可用 1 段树莓派语音唤醒/启动录像片段说明采集入口能力，用云端完整课堂 dashboard 展示真实课堂分析闭环，用 SAV-50 的 1-2 个典型切片和统计摘要说明外部验证。不要把 SAV-50 切片拼成单堂课堂，也不要把 SAV 样本说成树莓派采集或自采。
"""


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate Phase 3.10 three-side competition demo materials.")
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    args = parser.parse_args()

    output_dir = args.output_dir.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    files = {
        "three_side_workflow.md": THREE_SIDE_WORKFLOW,
        "pi_demo_boundary.md": PI_DEMO_BOUNDARY,
        "data_source_statement.md": DATA_SOURCE_STATEMENT,
    }
    for filename, content in files.items():
        (output_dir / filename).write_text(content, encoding="utf-8")

    print(f"PHASE310_COMPETITION_MATERIALS_DIR={output_dir}")
    for filename in files:
        print(f"PHASE310_OUTPUT_FILE={output_dir / filename}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
