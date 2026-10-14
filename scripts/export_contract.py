"""Run from repo root, then npm --prefix apps/desktop run generate:contracts."""
import json
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'apps/server'))
from app.main import app
Path('docs/openapi.json').write_text(json.dumps(app.openapi(),ensure_ascii=False,indent=2)+'\n')
