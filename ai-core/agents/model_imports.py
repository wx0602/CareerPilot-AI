from __future__ import annotations

import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]

# ai-core 目录名包含连字符，不能直接作为标准 Python 包名导入。
# 这里把仓库根目录加入 sys.path，便于复用公共 models.py。
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))
