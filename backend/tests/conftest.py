import os
import sys
from pathlib import Path

# Allow `import nightdesk` when pytest is launched from repo root or backend/.
BACKEND = Path(__file__).resolve().parents[1]
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

