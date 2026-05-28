from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys


REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from classroom_feedback_pipeline import retry_pending_uploads


def main() -> None:
    parser = argparse.ArgumentParser(description="Retry pending classroom feedback uploads.")
    parser.add_argument("--config-path", type=Path, default=None, help="Optional config.yaml path.")
    parser.add_argument("--pending-upload-dir", type=Path, default=None, help="Optional pending upload directory.")
    parser.add_argument("--limit", type=int, default=None, help="Optional max number of pending files to retry.")
    args = parser.parse_args()

    result = retry_pending_uploads(
        config_path=args.config_path,
        pending_upload_dir=args.pending_upload_dir,
        limit=args.limit,
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
