"""Check provenance, chronological evaluation and reported numeric results."""
from pathlib import Path
import csv,json,hashlib,math
ROOT=Path(__file__).resolve().parents[1]
manifest=json.loads((ROOT/'data/provenance.json').read_text())
for source in manifest['sources']:
    assert hashlib.sha256((ROOT/source['path']).read_bytes()).hexdigest()==source['sha256'],source['path']
s=json.loads((ROOT/'results/summary.json').read_text())
assert (s['main_n'],s['train_n'],s['validation_n'],s['test_n'])==(84,60,12,12)
assert s['all_fits_converged']
with (ROOT/'results/test_predictions.csv').open() as f: predictions=list(csv.DictReader(f))
assert len(predictions)==24
for row in predictions:
    assert row['origin']<row['Date']
    assert int(row['horizon']) in [1,2,3]
    assert all(math.isfinite(float(row[k])) for k in ['actual','forecast','lower80','upper80','lower95','upper95'])
    assert float(row['lower95'])<=float(row['lower80'])<=float(row['forecast'])<=float(row['upper80'])<=float(row['upper95'])
for model in ['Seasonal naive','SARIMA']:
    rows=[r for r in predictions if r['Model']==model]
    assert len(rows)==12 and len({r['Date'] for r in rows})==12
    assert all(sum(int(r['horizon'])==h for r in rows)==4 for h in [1,2,3])
    by_origin={r['origin'] for r in rows}; assert len(by_origin)==4
    assert all(sum(r['origin']==o for r in rows)==3 for o in by_origin)
    errors=[float(r['actual'])-float(r['forecast']) for r in rows]
    expected=next(r for r in s['test'] if r['Model']==model)
    assert math.isclose(sum(abs(e) for e in errors)/12,expected['MAE'],rel_tol=1e-10)
    assert math.isclose(math.sqrt(sum(e*e for e in errors)/12),expected['RMSE'],rel_tol=1e-10)
base,model=s['test']; gain=100*(base['MAE']-model['MAE'])/base['MAE']
assert math.isclose(gain,s['mae_improvement_percent'],rel_tol=1e-10)
import nbformat
nb=nbformat.read(ROOT/'electricity_project.ipynb',as_version=4); nbformat.validate(nb)
cells=[c for c in nb.cells if c.cell_type=='code']; assert len(cells)==7
assert all(c.execution_count is not None for c in cells)
assert not any(o.output_type=='error' for c in cells for o in c.outputs)
from pypdf import PdfReader
assert len(PdfReader(ROOT/'report/project_report.pdf').pages)==6
print('Verified source hashes, equal horizons, forecast chronology, recomputed metrics and executed notebook.')
print(f'SARIMA test MAE {model["MAE"]:.6f} TWh; reduction {gain:.4f}%.')
