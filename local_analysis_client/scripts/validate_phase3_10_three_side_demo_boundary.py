from __future__ import annotations

import argparse
from pathlib import Path


DEFAULT_MATERIALS_DIR = Path(r"C:\Users\lyy\Desktop\gradu\competition_materials")


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate Phase 3.10 three-side demo boundary materials.")
    parser.add_argument("--materials-dir", type=Path, default=DEFAULT_MATERIALS_DIR)
    args = parser.parse_args()

    materials_dir = args.materials_dir.resolve()
    workflow = materials_dir / "three_side_workflow.md"
    pi_boundary = materials_dir / "pi_demo_boundary.md"
    data_statement = materials_dir / "data_source_statement.md"

    workflow_text = _read_text(workflow)
    pi_text = _read_text(pi_boundary)
    data_text = _read_text(data_statement)
    all_text = "\n".join([workflow_text, pi_text, data_text])

    dir_present = materials_dir.exists() and materials_dir.is_dir()
    workflow_present = workflow.exists()
    pi_present = pi_boundary.exists()
    data_present = data_statement.exists()

    pi_wakeup = "语音唤醒" in all_text
    pi_recording = "语音指令" in all_text and "启动录像" in all_text
    local_role = all(term in all_text for term in ["本地分析端", "V1.1", "HTTP multipart"])
    cloud_role = all(term in all_text for term in ["云服务器端", "PostgreSQL", "dashboard"])
    phase37 = "phase37_full_classroom_sav_20200908_17" in all_text
    sav50 = "SAV-50" in all_text and "外部真实课堂切片验证集" in all_text
    no_sav_as_pi = "不是树莓派采集" in all_text
    no_sav_as_own = "不是自采" in all_text
    no_sav15 = "不宣称完整覆盖 SAV 15 类动作" in all_text
    ok = all(
        [
            dir_present,
            workflow_present,
            pi_present,
            data_present,
            pi_wakeup,
            pi_recording,
            local_role,
            cloud_role,
            phase37,
            sav50,
            no_sav_as_pi,
            no_sav_as_own,
            no_sav15,
        ]
    )

    print(f"PHASE310_COMPETITION_MATERIALS_DIR_PRESENT={_bool_text(dir_present)}")
    print(f"PHASE310_THREE_SIDE_WORKFLOW_PRESENT={_bool_text(workflow_present)}")
    print(f"PHASE310_PI_DEMO_BOUNDARY_PRESENT={_bool_text(pi_present)}")
    print(f"PHASE310_DATA_SOURCE_STATEMENT_PRESENT={_bool_text(data_present)}")
    print(f"PHASE310_PI_WAKEUP_ROLE_DOCUMENTED={_bool_text(pi_wakeup)}")
    print(f"PHASE310_PI_RECORDING_ROLE_DOCUMENTED={_bool_text(pi_recording)}")
    print(f"PHASE310_LOCAL_ANALYZER_ROLE_DOCUMENTED={_bool_text(local_role)}")
    print(f"PHASE310_CLOUD_PLATFORM_ROLE_DOCUMENTED={_bool_text(cloud_role)}")
    print(f"PHASE310_PHASE37_FINAL_SAMPLE_DOCUMENTED={_bool_text(phase37)}")
    print(f"PHASE310_SAV50_VALIDATION_ROLE_DOCUMENTED={_bool_text(sav50)}")
    print(f"PHASE310_NO_SAV_AS_PI_CAPTURE={_bool_text(no_sav_as_pi)}")
    print(f"PHASE310_NO_SAV_AS_OWN_CAPTURE={_bool_text(no_sav_as_own)}")
    print(f"PHASE310_NO_SAV15_OVERCLAIM={_bool_text(no_sav15)}")
    print(f"PHASE310_THREE_SIDE_DEMO_BOUNDARY_OK={_bool_text(ok)}")
    return 0 if ok else 1


def _read_text(path: Path) -> str:
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8")


def _bool_text(value: bool) -> str:
    return "true" if value else "false"


if __name__ == "__main__":
    raise SystemExit(main())
