from __future__ import annotations

import importlib.util
from pathlib import Path
import sys


def _load_relocated_module():
    module_path = Path(__file__).resolve().parent / "local-processor" / "core" / "classroom_feedback_pipeline.py"
    spec = importlib.util.spec_from_file_location("local_processor_core_classroom_feedback_pipeline", module_path)
    if spec is None or spec.loader is None:
        raise ImportError(f"无法加载课堂反馈主链路模块: {module_path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


_MODULE = _load_relocated_module()

for _name in dir(_MODULE):
    if _name.startswith("_"):
        continue
    globals()[_name] = getattr(_MODULE, _name)
