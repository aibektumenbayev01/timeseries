"""Compatibility entry point: build the current report and slides from shared CSV results."""
from pathlib import Path
import runpy
runpy.run_path(str(Path(__file__).with_name("build_documents.py")),run_name="__main__")
