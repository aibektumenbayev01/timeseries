"""Rebuild frozen-data analysis, notebook and editable documents; optionally compile PDFs."""
from pathlib import Path
import subprocess,sys,argparse,shutil
ROOT=Path(__file__).resolve().parents[1]
p=argparse.ArgumentParser()
p.add_argument('--latex',action='store_true',help='Compile the updated report and Beamer PDFs with pdfLaTeX')
a=p.parse_args()
for name in ['extract_data.py','check_sources.py','build_notebook.py','build_documents.py']:
    subprocess.run([sys.executable,str(ROOT/'scripts'/name)],cwd=ROOT,check=True)
if a.latex:
    exe=shutil.which('pdflatex')
    if not exe:raise SystemExit('Install a TeX distribution or compile each main.tex in Overleaf.')
    for folder in ['report_ams_style','presentation']:
        for _ in range(2):subprocess.run([exe,'-interaction=nonstopmode','-halt-on-error','main.tex'],cwd=ROOT/folder,check=True)
    subprocess.run([sys.executable,str(ROOT/'scripts/sync_documents.py')],cwd=ROOT,check=True)
subprocess.run([sys.executable,str(ROOT/'scripts/verify_results.py')],cwd=ROOT,check=True)
print('Reproduction complete. PDF refresh requires --latex.')
