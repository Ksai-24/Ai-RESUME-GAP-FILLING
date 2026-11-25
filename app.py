"""Keep the existing Render and local Streamlit entry point."""
import runpy
import sys
from pathlib import Path

source = Path(__file__).resolve().parent / "SOURCE CODE"
sys.path.insert(0, str(source))
try:
    runpy.run_path(str(source / "app.py"), run_name="__main__")
finally:
    sys.path.pop(0)
