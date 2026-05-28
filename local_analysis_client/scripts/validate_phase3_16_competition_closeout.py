from __future__ import annotations

import argparse
import re
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_MATERIALS_DIR = REPO_ROOT.parent / "competition_materials"

FILES = {
    "project_summary": "competition_project_summary.md",
    "technical_solution": "technical_solution.md",
    "demo_video_script": "demo_video_script.md",
    "final_demo_runbook": "final_demo_runbook.md",
    "final_acceptance_checklist": "final_acceptance_checklist.md",
    "known_limitations": "known_limitations.md",
    "data_validation_summary": "data_validation_summary.md",
    "judge_qna": "judge_qna.md",
    "asr_multimodal_summary": "asr_multimodal_summary.md",
}


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate Phase 3.16 competition closeout materials.")
    parser.add_argument("--materials-dir", type=Path, default=DEFAULT_MATERIALS_DIR)
    args = parser.parse_args()

    materials_dir = args.materials_dir.resolve()
    texts = {key: read_text(materials_dir / filename) for key, filename in FILES.items()}
    all_text = "\n".join(texts.values())

    present = {key: (materials_dir / filename).exists() for key, filename in FILES.items()}
    qna_count = len(re.findall(r"^## Q\d+\.", texts["judge_qna"], flags=re.MULTILINE))
    three_side = all(term in all_text for term in ["树莓派语音交互式采集端", "本地多模态课堂分析端", "云端教师/管理员平台"])
    local_asr = all(term in all_text for term in ["本地离线 ASR", "faster-whisper base"])
    transcript_764 = "transcript segments=764" in all_text or "transcript=764" in all_text or "transcript 764" in all_text or "transcript 764 段" in all_text
    question_35 = "教师提问候选事件=35" in all_text or "question_events=35" in all_text or "教师提问候选 35" in all_text
    response_16 = "检测到响应=16" in all_text or "response_detected=16" in all_text or "检测到响应 16" in all_text
    auto_upload = "multipart" in all_text and "POST /api/interaction-results/with-video" in all_text and "自动上传" in all_text
    phase314 = "phase314_asr_full_classroom_sav_20200908_17" in all_text and "/dashboard?result_id=phase314_asr_full_classroom_sav_20200908_17" in all_text
    sav50 = all(term in all_text for term in ["SAV-50", "total=50", "raise_hand=16/29", "stand=25/46"])
    data_boundary = "SAV 外部公开课堂视频" in all_text and "不是树莓派采集" in all_text and "不是自采" in all_text
    no_sav_pi = "不是树莓派采集" in all_text and "树莓派端展示采集入口能力" in all_text
    no_sav_own = "不是自采" in all_text
    no_sav15 = "不宣称完整覆盖 SAV 15 类动作" in all_text
    no_teacher_overclaim = "不做精准教师身份判断" in all_text and "没有说话人分离" in all_text
    limitations = all(term in texts["known_limitations"] for term in ["不是自采", "faster-whisper base", "没有说话人分离", "不覆盖 SAV 15 类全动作"])
    demo_ready = all(term in texts["demo_video_script"] for term in ["旁白", "画面", "云端教师端", "SAV-50 验证"])
    ready = all(present.values()) and all(
        [
            three_side,
            local_asr,
            transcript_764,
            question_35,
            response_16,
            auto_upload,
            phase314,
            sav50,
            data_boundary,
            no_sav_pi,
            no_sav_own,
            no_sav15,
            no_teacher_overclaim,
            limitations,
            demo_ready,
            qna_count >= 12,
        ]
    )

    print(f"PHASE316_COMPETITION_MATERIALS_DIR_PRESENT={bool_text(materials_dir.exists())}")
    print(f"PHASE316_PROJECT_SUMMARY_PRESENT={bool_text(present['project_summary'])}")
    print(f"PHASE316_TECHNICAL_SOLUTION_PRESENT={bool_text(present['technical_solution'])}")
    print(f"PHASE316_DEMO_VIDEO_SCRIPT_PRESENT={bool_text(present['demo_video_script'])}")
    print(f"PHASE316_FINAL_DEMO_RUNBOOK_PRESENT={bool_text(present['final_demo_runbook'])}")
    print(f"PHASE316_FINAL_ACCEPTANCE_CHECKLIST_PRESENT={bool_text(present['final_acceptance_checklist'])}")
    print(f"PHASE316_KNOWN_LIMITATIONS_PRESENT={bool_text(present['known_limitations'])}")
    print(f"PHASE316_DATA_VALIDATION_SUMMARY_PRESENT={bool_text(present['data_validation_summary'])}")
    print(f"PHASE316_JUDGE_QNA_PRESENT={bool_text(present['judge_qna'])}")
    print(f"PHASE316_ASR_MULTIMODAL_SUMMARY_PRESENT={bool_text(present['asr_multimodal_summary'])}")
    print(f"PHASE316_THREE_SIDE_ARCHITECTURE_DOCUMENTED={bool_text(three_side)}")
    print(f"PHASE316_LOCAL_ASR_DOCUMENTED={bool_text(local_asr)}")
    print(f"PHASE316_ASR_TRANSCRIPT_764_DOCUMENTED={bool_text(transcript_764)}")
    print(f"PHASE316_QUESTION_EVENTS_35_DOCUMENTED={bool_text(question_35)}")
    print(f"PHASE316_RESPONSE_DETECTED_16_DOCUMENTED={bool_text(response_16)}")
    print(f"PHASE316_AUTO_UPLOAD_DOCUMENTED={bool_text(auto_upload)}")
    print(f"PHASE316_PHASE314_FINAL_DASHBOARD_DOCUMENTED={bool_text(phase314)}")
    print(f"PHASE316_SAV50_VALIDATION_DOCUMENTED={bool_text(sav50)}")
    print(f"PHASE316_DATA_SOURCE_BOUNDARY_DOCUMENTED={bool_text(data_boundary)}")
    print(f"PHASE316_NO_SAV_AS_PI_CAPTURE={bool_text(no_sav_pi)}")
    print(f"PHASE316_NO_SAV_AS_OWN_CAPTURE={bool_text(no_sav_own)}")
    print(f"PHASE316_NO_SAV15_OVERCLAIM={bool_text(no_sav15)}")
    print(f"PHASE316_NO_TEACHER_IDENTITY_OVERCLAIM={bool_text(no_teacher_overclaim)}")
    print(f"PHASE316_LIMITATIONS_DOCUMENTED={bool_text(limitations)}")
    print(f"PHASE316_DEMO_SCRIPT_READY={bool_text(demo_ready)}")
    print(f"PHASE316_JUDGE_QNA_COUNT={qna_count}")
    print(f"PHASE316_COMPETITION_CLOSEOUT_READY={bool_text(ready)}")
    return 0 if ready else 1


def read_text(path: Path) -> str:
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8", errors="ignore")


def bool_text(value: bool) -> str:
    return "true" if value else "false"


if __name__ == "__main__":
    raise SystemExit(main())
