from __future__ import annotations

import argparse
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT_DIR = REPO_ROOT.parent / "competition_materials"

PROJECT_NAME = "智能课堂行为分析与教学反馈平台"
FINAL_ANALYSIS_ID = "phase314_asr_full_classroom_sav_20200908_17"
FINAL_DASHBOARD_URL = "http://<cloud-host>:8011/dashboard?result_id=phase314_asr_full_classroom_sav_20200908_17"
ASR_MODEL_PATH = r"C:\Users\lyy\Desktop\gradu\asr_models\faster-whisper-base"
TRANSCRIPT_PATH = (
    r"C:\Users\lyy\Desktop\gradu\real_classroom_samples\asr_results"
    r"\phase312_asr_full_classroom_sav_20200908_17\transcript.json"
)
VIDEO_PATH = r"C:\Users\lyy\Desktop\gradu\real_classroom_samples\videos\local_imported_sav_full_classroom_20200908_17.mp4"
SAV50_SUMMARY_PATH = r"C:\Users\lyy\Desktop\gradu\sav_dataset\SAV\reports\sav50_competition_validation_summary.md"


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate Phase 3.16 competition closeout materials.")
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    args = parser.parse_args()

    output_dir = args.output_dir.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    for filename, content in build_materials().items():
        (output_dir / filename).write_text(content, encoding="utf-8")

    print(f"PHASE316_OUTPUT_DIR={output_dir}")
    for filename in build_materials():
        print(f"PHASE316_OUTPUT_FILE={output_dir / filename}")
    return 0


def build_materials() -> dict[str, str]:
    return {
        "competition_project_summary.md": competition_project_summary(),
        "technical_solution.md": technical_solution(),
        "demo_video_script.md": demo_video_script(),
        "final_demo_runbook.md": final_demo_runbook(),
        "final_acceptance_checklist.md": final_acceptance_checklist(),
        "known_limitations.md": known_limitations(),
        "data_validation_summary.md": data_validation_summary(),
        "judge_qna.md": judge_qna(),
        "asr_multimodal_summary.md": asr_multimodal_summary(),
    }


def competition_project_summary() -> str:
    return f"""# {PROJECT_NAME}项目总结

## 项目背景

课堂教学反馈通常依赖人工听评课和课后主观记录，难以及时覆盖完整课堂过程。本项目面向课堂视频复盘、行为趋势观察和教师教学反馈，构建树莓派语音交互式采集端、本地多模态课堂分析端、云端教师/管理员平台的三端闭环。

## 目标用户

- 教师：查看课堂视频、行为趋势、ASR 摘要、教师提问候选和响应对齐，辅助课后复盘。
- 管理员：查看数据接入、上传状态、视频可播放状态和班级样本管理。

## 三端架构

1. 树莓派语音交互式采集端：展示语音唤醒、语音指令、启动录像和采集入口能力。
2. 本地多模态课堂分析端：执行本地视觉行为分析、本地音频提取、本地离线 ASR 转写、提问候选生成和视觉响应对齐。
3. 云端教师/管理员平台：接收 multipart 视频 + JSON，保存 raw JSON、写入 PostgreSQL、通过 /uploads 播放视频，并在 dashboard 展示分析结果。

## 核心功能

- 完整课堂视频与分析 JSON 自动上传。
- 本地视觉行为分析和行为趋势生成。
- 本地离线 ASR 转写，transcript segments=764。
- 教师提问候选事件=35。
- 视觉响应对齐=35，检测到响应=16。
- 云端 dashboard 展示视频、行为趋势、ASR 摘要、提问候选和响应对齐。
- SAV-50 外部真实课堂切片验证报告。

## 最终演示闭环

最终主样本 analysis_id={FINAL_ANALYSIS_ID}，dashboard={FINAL_DASHBOARD_URL}。演示闭环为：树莓派采集入口说明 -> 本地视觉 + ASR 多模态分析 -> multipart 自动上传 -> 云端教师 dashboard 展示 -> SAV-50 外部验证摘要。

## 数据来源说明

最终完整课堂样本来自 SAV 外部公开课堂视频，不是树莓派采集，不是自采。树莓派端用于展示采集入口能力，不承担 SAV 样本来源。SAV-50 是外部真实课堂切片验证集，不是 dashboard 主样本，不宣称完整覆盖 SAV 15 类动作。

## 项目创新点

- 将低成本采集入口、本地多模态分析和云端教学反馈形成闭环。
- 将视频行为趋势、离线 ASR 转写、教师提问候选和视觉响应对齐放到同一个课堂复盘视图。
- 保留数据来源和能力边界，不把外部数据误表述为自采数据。

## 当前完成状态

Phase 3.14 已完成 ASR 增强完整课堂样本云端上传，Phase 3.15 已完成云端 dashboard ASR 展示。Phase 3.16 汇总比赛文档、演示视频脚本、最终 runbook、验收清单、已知限制和答辩 Q&A。
"""


def technical_solution() -> str:
    return f"""# 技术方案

## 系统架构

系统采用三端架构：树莓派语音交互式采集端、本地多模态课堂分析端、云端教师/管理员平台。

## 树莓派端职责

树莓派端负责语音唤醒、语音指令、启动录像和采集入口展示。它证明系统具备边缘采集入口能力，但最终完整课堂 SAV 样本不是树莓派采集，也不是自采。

## 本地分析端职责

本地端负责课堂视频导入或接收、视觉行为分析、音频提取、本地离线 ASR 转写、教师提问候选生成、视觉响应对齐、V1.1 JSON 组装和 multipart 自动上传。

## 云端职责

云端负责接收视频和 JSON、保存 raw JSON、写入 PostgreSQL、将视频保存到 /uploads 视频目录，并通过 /dashboard、/teacher/results、/teacher/reports、/admin/ingestion 展示教师端和管理端能力。

## 数据流

树莓派采集/视频导入 -> 本地视觉分析 -> 本地音频提取 -> 本地 ASR 转写 -> 提问候选与视觉响应对齐 -> multipart 上传 -> 云端保存/入库 -> dashboard 展示。

## 接口

- POST /api/interaction-results：兼容旧 JSON 上传。
- POST /api/interaction-results/with-video：接收 multipart/form-data，同时上传完整课堂视频和分析 JSON。

## 云端页面

- /dashboard：最终 ASR 增强完整课堂 dashboard。
- /teacher/results：教师端结果列表和 detail API。
- /teacher/reports：教师端报告。
- /admin/ingestion：管理员接入状态和视频可播放状态。

## 存储

- raw JSON：保存云端接收到的原始分析结果。
- PostgreSQL：保存课堂分析索引、分数、视频状态和可查询 detail 数据。
- /uploads 视频目录：保存云端可播放课堂视频。
- transcript / question_events / interaction_alignment：作为 V1.1 extra-compatible 字段进入 ASR 增强 payload。

## 数据边界说明

最终完整课堂样本来自 SAV 外部公开课堂视频，不是树莓派采集，不是自采。树莓派端展示采集入口能力。当前没有说话人分离，因此 ASR 输出的是教师提问候选事件，不做精准教师身份判断。
"""


def demo_video_script() -> str:
    return f"""# 演示视频脚本

## 1. 开场 10-15 秒

旁白：本项目是{PROJECT_NAME}，采用树莓派采集端、本地多模态分析端和云端教师平台三端架构，目标是把课堂视频、行为分析、语音转写和教学反馈放到同一个复盘闭环中。

画面：展示系统标题页或三端架构图，快速出现树莓派、本地分析端、云端 dashboard 三个模块。

## 2. 树莓派端 20-30 秒

旁白：树莓派端用于展示采集入口能力，包括语音唤醒、语音指令和启动录像。这里展示的是入口能力，不把 SAV 外部样本说成树莓派采集。

画面：展示语音唤醒、语音指令开始录像、录像文件生成或采集素材入口。

## 3. 本地分析端 40-60 秒

旁白：本地端接收或导入课堂视频，执行视觉行为分析；随后提取音频，使用离线 faster-whisper base 进行 ASR 转写，生成 764 段 transcript，并基于规则生成 35 个教师提问候选事件，再与视觉响应窗口对齐。

画面：展示完整课堂视频路径、ASR transcript 路径、question_events.csv、interaction_alignment.csv，以及本地脚本输出 marker。

## 4. 自动上传 20-30 秒

旁白：本地端通过 POST /api/interaction-results/with-video 自动上传视频和 ASR 增强 JSON，不再手动复制视频到服务器。

画面：展示上传脚本运行，显示 multipart 上传成功、video_url 返回和 analysis_id={FINAL_ANALYSIS_ID}。

## 5. 云端教师端 90-120 秒

旁白：云端 dashboard 展示完整课堂视频、行为趋势、ASR 摘要、提问候选和响应对齐。当前没有说话人分离，因此这里显示的是教师提问候选事件，不做精准教师身份判断。

画面：打开 {FINAL_DASHBOARD_URL}，播放视频，依次展示行为趋势、ASR 转写摘要、35 个提问候选、35 条响应对齐、16 个检测到响应，以及教师报告页。

## 6. SAV-50 验证 30-45 秒

旁白：除完整课堂主样本外，我们使用 SAV-50 外部真实课堂切片验证核心行为识别可信度。50 个切片全部分析成功，raise_hand 为 16/29，stand 为 25/46。该验证只覆盖举手、站立等核心行为，不宣称完整覆盖 SAV 15 类动作。

画面：展示 SAV-50 summary、talking points 和典型命中/漏检样本表。

## 7. 结尾 10-20 秒

旁白：系统完成了从采集入口、本地多模态分析到云端教学反馈的闭环。当前定位是比赛原型和教学反馈演示系统，后续真实部署还需要更多自采课堂数据、说话人分离和长期校准。

画面：回到三端架构和 dashboard，突出“视频 + 行为 + ASR + 反馈”的完整闭环。
"""


def final_demo_runbook() -> str:
    return f"""# 最终演示 Runbook

## 演示前检查

- 树莓派端：确认语音唤醒、语音指令、启动录像演示素材可用。
- 本地端：确认 Python 环境、脚本目录和本地结果目录可用。
- ASR 模型路径：`{ASR_MODEL_PATH}`。
- ASR transcript 路径：`{TRANSCRIPT_PATH}`。
- 完整课堂视频路径：`{VIDEO_PATH}`。
- Phase 3.14 dashboard URL：`{FINAL_DASHBOARD_URL}`。
- 云端：确认 `<cloud-host>:8011` 可访问，/health 正常，教师账号可登录。
- 网络：确认本地机器能访问云端 8011 端口。
- 浏览器：建议提前登录教师端，打开 dashboard、reports、admin ingestion 备用标签页。
- SAV-50 报告路径：`{SAV50_SUMMARY_PATH}`。

## 演示顺序

1. 三端架构和数据来源口径。
2. 树莓派语音唤醒和启动录像入口。
3. 本地端展示完整课堂视频、视觉分析、ASR transcript、question_events、interaction_alignment。
4. 展示 multipart 自动上传链路。
5. 打开 Phase 3.14 ASR 增强 dashboard。
6. 展示 SAV-50 验证摘要。
7. 说明已知限制和后续计划。

## 云服务异常处理

如果云服务没启动或 8011 不可达，先检查服务状态、网络、防火墙和端口监听情况。不要把自动重启命令作为默认演示动作；演示前应提前确认云端稳定运行。
"""


def final_acceptance_checklist() -> str:
    return f"""# 最终验收清单

- [x] 树莓派语音控制：已形成演示边界和入口说明。
- [x] 本地视觉分析：已用于完整课堂样本和 SAV-50 验证。
- [x] 本地 ASR 转写：使用离线 faster-whisper base，transcript segments=764。
- [x] 提问候选生成：teacher question candidates=35。
- [x] 视觉响应对齐：interaction_alignment=35。
- [x] 检测到响应：response_detected=16。
- [x] 自动上传：POST /api/interaction-results/with-video 已验证。
- [x] ASR 增强完整课堂 dashboard：{FINAL_DASHBOARD_URL}。
- [x] 同源视频/分析：Phase 3.14 使用完整课堂视频和对应 ASR 增强 payload。
- [x] SAV-50 报告：50 个外部真实课堂切片验证，analysis_success=50/50。
- [x] 三端流程材料：three_side_workflow、pi_demo_boundary、data_source_statement 已生成。
- [x] 数据来源说明：SAV 外部公开课堂视频，不是树莓派采集，不是自采。
- [x] 页面口径说明：ASR 提问为候选事件，不做精准教师身份判断。
- [x] 演示脚本：demo_video_script.md 已生成。
- [x] 已知限制：known_limitations.md 已生成。
"""


def known_limitations() -> str:
    return """# 已知限制

- 最终完整课堂样本来自 SAV 外部公开数据，不是自采。
- 树莓派端展示采集入口能力，不承担 SAV 样本来源。
- 当前 ASR 使用离线 faster-whisper base，受音频质量、语言、口音和噪声影响。
- 当前没有说话人分离，因此为教师提问候选事件，不做精准教师身份判断。
- SAV-50 只验证 raise_hand / stand 等核心行为，不覆盖 SAV 15 类全动作。
- raise_hand=16/29, 55.2%；stand=25/46, 54.3%。这些命中率不是高精度工业级指标。
- 当前系统适合比赛原型和教学反馈场景演示，后续真实部署需要更多自采课堂数据、说话人分离、长期校准和更严格的隐私合规流程。
"""


def data_validation_summary() -> str:
    return f"""# 数据验证摘要

## Phase 3.14 ASR 增强完整课堂样本

- analysis_id={FINAL_ANALYSIS_ID}
- dashboard={FINAL_DASHBOARD_URL}
- 完整课堂视频：SAV 外部公开课堂视频。
- 本地离线 ASR transcript=764。
- 教师提问候选 question_events=35。
- 视觉响应对齐 interaction_alignment=35。
- 检测到响应 response_detected=16。
- 自动上传链路：本地通过 multipart 上传视频 + JSON 到 POST /api/interaction-results/with-video。

## SAV-50 外部真实课堂切片验证

- total=50。
- question_interaction=25。
- classroom_routine_standing=15。
- classroom_routine_bending=10。
- analysis_success=50/50。
- raise_hand=16/29, 55.2%。
- stand=25/46, 54.3%。

## 数据来源和结论边界

完整课堂主样本和 SAV-50 均来自 SAV 外部公开课堂视频，不是树莓派采集，不是自采。SAV-50 是外部真实课堂切片验证集，不是 dashboard 主样本，不宣称完整覆盖 SAV 15 类动作。当前结论用于比赛原型和教学反馈演示，不夸大为工业级高精度识别结果。
"""


def judge_qna() -> str:
    return f"""# 答辩 Q&A

## Q1. 你们的数据是不是自己采集的？

不是。最终完整课堂样本来自 SAV 外部公开课堂视频，不是自采。我们会明确说明数据来源，避免把外部数据包装成自建数据。

## Q2. 树莓派端和 SAV 数据是什么关系？

树莓派端用于展示语音唤醒、语音指令、启动录像和采集入口能力。SAV 样本是外部公开课堂视频，用于完整课堂分析展示和外部验证，两者不混淆。

## Q3. 为什么使用 SAV 外部数据？

比赛阶段需要可复现、可说明的真实课堂素材。SAV 提供外部公开课堂视频，适合验证完整课堂分析链路和外部真实课堂切片验证。

## Q4. 50 个切片够不够？

SAV-50 定位为外部真实课堂切片验证集，用于补充可信度说明，不等同于大规模评测。它能说明系统在真实课堂片段上对举手、站立等核心行为做过验证。

## Q5. 准确率为什么不是很高？

我们没有把结果包装成高精度工业级指标。raise_hand=16/29, 55.2%；stand=25/46, 54.3%。外部公开视频视角、遮挡、多人重叠和标注差异都会影响命中率。

## Q6. 云端展示的视频和分析是否同源？

是。最终主样本 {FINAL_ANALYSIS_ID} 使用同一完整课堂视频生成视觉分析、ASR transcript、提问候选和响应对齐，并通过 multipart 自动上传到云端。

## Q7. 是否支持自动上传？

支持。本地端通过 POST /api/interaction-results/with-video 自动上传完整课堂视频和 ASR 增强 JSON，不需要手动复制视频到云服务器目录。

## Q8. 是否可以真实课堂部署？

当前适合比赛原型和教学反馈演示。真实部署还需要更多自采课堂数据、隐私合规、说话人分离、长期校准和学校网络环境适配。

## Q9. 和普通视频监控有什么区别？

普通监控主要记录视频。本项目面向教学反馈，把课堂视频、行为趋势、ASR 转写、教师提问候选、视觉响应对齐和云端报告结合起来。

## Q10. 项目的创新点是什么？

创新点在三端闭环和多模态反馈：树莓派采集入口、本地视觉 + ASR 分析、云端教学平台展示，并把提问候选与视觉响应窗口对齐。

## Q11. ASR 如何判断教师提问？

系统使用离线 ASR 生成 transcript，再根据中英文疑问词、互动触发语和课堂指令词生成教师提问候选，同时与视觉响应窗口做对齐。

## Q12. 没有说话人分离会不会影响提问判断？

会影响身份归属判断。因此我们只称为教师提问候选事件，标记 teacher_candidate，不做精准教师身份判断。

## Q13. SAV-50 是否覆盖 SAV 15 类动作？

不覆盖。SAV-50 只验证 raise_hand / stand 等核心课堂行为，不宣称完整覆盖 SAV 15 类动作。

## Q14. Phase 3.14 dashboard 是最终主样本吗？

是。最终 ASR 增强主样本 analysis_id={FINAL_ANALYSIS_ID}，dashboard={FINAL_DASHBOARD_URL}。Phase 3.7 可作为非 ASR 备选样本。
"""


def asr_multimodal_summary() -> str:
    return f"""# ASR 多模态层总结

## 本地端离线 ASR

本地端使用离线 faster-whisper base，对完整课堂视频提取音频并生成 transcript。ASR 模型路径为 `{ASR_MODEL_PATH}`。

## 音频提取和转写

完整课堂视频先提取为 16kHz mono WAV，再进行本地 ASR 转写。最终 transcript 764 段。

## 提问候选和视觉响应对齐

系统基于 ASR 文本规则生成教师提问候选 35 个，并与视觉响应窗口对齐 35 条，其中检测到响应 16 个。

## 边界

当前没有说话人分离，因此这些事件是 teacher question candidates，不做精准教师身份判断。ASR 受音频质量、语言、口音和噪声影响。

## 云端展示效果

Phase 3.14 ASR 增强完整课堂样本已上传云端，dashboard 展示完整课堂视频、行为趋势、ASR 摘要、提问候选和响应对齐。最终 dashboard：{FINAL_DASHBOARD_URL}。
"""


if __name__ == "__main__":
    raise SystemExit(main())
