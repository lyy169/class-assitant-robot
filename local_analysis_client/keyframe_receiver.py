from __future__ import annotations

import importlib.util
from pathlib import Path
import sys


def _load_relocated_module():
    module_path = Path(__file__).resolve().parent / "local-processor" / "api" / "keyframe_receiver.py"
    spec = importlib.util.spec_from_file_location("local_processor_api_keyframe_receiver", module_path)
    if spec is None or spec.loader is None:
        raise ImportError(f"无法加载归位后的接收器模块: {module_path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


_MODULE = _load_relocated_module()

app = _MODULE.app
health = _MODULE.health
receive_keyframes = _MODULE.receive_keyframes
main = _MODULE.main


if __name__ == "__main__":
    main()
