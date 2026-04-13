"""Root conftest: ensure this worktree's src/ is first on sys.path."""
import sys
from pathlib import Path

_src = str(Path(__file__).resolve().parent / "src")
if _src not in sys.path:
    sys.path.insert(0, _src)

# Force reimport of bot package from this worktree's src
for key in list(sys.modules.keys()):
    if key == "bot" or key.startswith("bot."):
        del sys.modules[key]
