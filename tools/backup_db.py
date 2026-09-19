from pathlib import Path
import shutil, sys
root=Path(__file__).resolve().parents[1]
db=root/"data"/"taranom.db"
out=root/"data"/"backups"
out.mkdir(parents=True,exist_ok=True)
if not db.exists():
    print("No database found:", db); sys.exit(1)
from datetime import datetime
target=out/f"taranom_{datetime.now():%Y%m%d_%H%M%S}.db"
shutil.copy2(db,target)
print(target)
