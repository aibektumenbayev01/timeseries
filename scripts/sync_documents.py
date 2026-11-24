"""Synchronize compiled report aliases and plain-text reading copies."""
from pathlib import Path
import shutil
from pypdf import PdfReader
ROOT=Path(__file__).resolve().parents[1]
source=ROOT/'report_ams_style/main.pdf'
text='\n\n'.join(p.extract_text() for p in PdfReader(source).pages)
for folder in ['report','report_revised']:
    shutil.copy2(source,ROOT/folder/'main.pdf')
    (ROOT/folder/'report_text.txt').write_text(text)
shutil.copy2(source,ROOT/'report/project_report.pdf')
(ROOT/'report_revised/corrected_text.txt').write_text(text)
print('Synchronized current report PDFs and reading copies.')
