"""Rebuild analysis, executed notebook, PDFs and LaTeX; optionally compile TeX."""
from pathlib import Path
import subprocess,sys,argparse,shutil
ROOT=Path(__file__).resolve().parents[1]
parser=argparse.ArgumentParser()
parser.add_argument('--latex',action='store_true',help='Also compile report/main.pdf (requires pdflatex)')
args=parser.parse_args()
for name in ['extract_data.py','check_sources.py','build_notebook.py','build_report.py','build_latex.py','verify_results.py']:
    subprocess.run([sys.executable,str(ROOT/'scripts'/name)],cwd=ROOT,check=True)
if args.latex:
    executable=shutil.which('pdflatex')
    if not executable: raise SystemExit('Install a TeX distribution or compile report/main.tex in Overleaf.')
    for _ in range(2):
        subprocess.run([executable,'-interaction=nonstopmode','-halt-on-error','main.tex'],cwd=ROOT/'report',check=True)
print('Reproduction complete.')
