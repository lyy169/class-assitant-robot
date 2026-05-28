from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys


REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from classroom_feedback_pipeline import analyze_delivery_package


def main() -> None:
    parser = argparse.ArgumentParser(description="Analyze a Raspberry Pi classroom delivery package and emit feedback JSON v1.1.")
    parser.add_argument("package_dir", type=Path, help="Directory containing video/audio/metadata.json from Raspberry Pi.")
    parser.add_argument("--config-path", type=Path, default=None, help="Optional config.yaml path.")
    parser.add_argument("--output-dir", type=Path, default=None, help="Optional output directory for generated JSON.")
    parser.add_argument("--pending-upload-dir", type=Path, default=None, help="Optional fallback directory for failed uploads.")
    parser.add_argument("--upload-mode", choices=["auto", "http", "directory"], default="auto")
    args = parser.parse_args()

    result = analyze_delivery_package(
        args.package_dir,
        config_path=args.config_path,
        output_dir=args.output_dir,
        pending_upload_dir=args.pending_upload_dir,
        upload_mode=args.upload_mode,
    )
    delivery = result.get("delivery", {})
    print(f"analysis_id: {result['analysis_id']}")
    print(f"output_path: {result['output_path']}")
    print(f"upload_mode: {delivery.get('mode')}")
    print(f"http_status: {delivery.get('http_status')}")
    if delivery.get("fallback_reason"):
        print(f"fallback_reason: {delivery['fallback_reason']}")
    if delivery.get("response_preview") is not None:
        print("response_preview:")
        print(json.dumps(delivery["response_preview"], ensure_ascii=False, indent=2))
    if delivery.get("target"):
        print(f"delivery_target: {delivery['target']}")
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
