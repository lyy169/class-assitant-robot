from __future__ import annotations

import importlib.util
from pathlib import Path
import sys


def _load_relocated_module():
    module_path = Path(__file__).resolve().parent / "local-processor" / "train" / "train_interaction_model.py"
    spec = importlib.util.spec_from_file_location("local_processor_train_train_interaction_model", module_path)
    if spec is None or spec.loader is None:
        raise ImportError(f"无法加载归位后的训练模块: {module_path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


_MODULE = _load_relocated_module()

for _name in dir(_MODULE):
    if _name.startswith("_"):
        continue
    globals()[_name] = getattr(_MODULE, _name)


if __name__ == "__main__":
    main()
