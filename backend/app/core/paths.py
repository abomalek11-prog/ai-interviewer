import os
from pathlib import Path

# Overridable so production can keep uploads on a persistent volume (e.g. /data/uploads);
# the default sits inside the code checkout, which is fine locally but wiped on redeploy.
UPLOADS_DIR = Path(os.getenv("UPLOADS_DIR") or Path(__file__).resolve().parent.parent.parent / "uploads")
