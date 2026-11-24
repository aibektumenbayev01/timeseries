"""Independent checks of provenance, benchmark chronology, metrics and document values."""
from pathlib import Path
import csv,json,hashlib,math,ast
import numpy as np
import pandas as pd
ROOT=Path(__file__).resolve().parents[1]
def read(name):
    with (ROOT/'results'/name).open() as f:return list(csv.DictReader(f))
def close(a,b):assert math.isclose(float(a),float(b),rel_tol=1e-10,abs_tol=1e-10),(a,b)
for source in json.loads((ROOT/'data/provenance.json').read_text())['sources']:
    assert hashlib.sha256((ROOT/source['path']).read_bytes()).hexdigest()==source['sha256'],source['path']
s=json.loads((ROOT/'results/summary.json').read_text());assert (s['main_n'],s['train_n'],s['validation_n'],s['test_n'])==(84,60,12,12)
assert s['all_fits_converged'] and s['selected_order']==[1,0,0] and s['selected_seasonal_order']==[0,1,1,12] and s['trend']=='c'
rows=read('test_predictions.csv');assert len(rows)==36
models=['Seasonal naive','Growth-adjusted seasonal naive','SARIMA']
metrics={r['Model']:r for r in read('test_scores.csv')};hs={(r['Model'],int(r['horizon'])):r for r in read('horizon_scores.csv')}
raw=pd.read_csv(ROOT/'data/kazakhstan_generation_snapshot.csv',parse_dates=['Date']).set_index('Date').Generation_TWh
for name in models:
    group=[r for r in rows if r['Model']==name]
    assert len(group)==12 and len({r['Date'] for r in group})==12
    assert {r['origin'][:7] for r in group}=={'2024-12','2025-03','2025-06','2025-09'}
    ee=[]
    for r in group:
        date=pd.Timestamp(r['Date']);cutoff=pd.Timestamp(r['origin']);assert cutoff<date
        assert date==cutoff+pd.DateOffset(months=int(r['horizon']))
        close(r['actual'],raw.loc[date]);ee.append(float(r['actual'])-float(r['forecast']))
        if name=='Growth-adjusted seasonal naive':
            # Independent calendar-date computation, not the analysis diff implementation.
            months=pd.date_range(end=cutoff,periods=12,freq='MS')
            adjustment=sum(float(raw.loc[d]-raw.loc[d-pd.DateOffset(years=1)]) for d in months)/12
            close(r['growth_adjustment_TWh'],adjustment)
            close(r['forecast'],float(raw.loc[date-pd.DateOffset(years=1)])+adjustment)
            assert all(not r[k] for k in ['lower80','upper80','lower95','upper95'])
        else:
            lo95,lo80,fc,hi80,hi95=[float(r[k]) for k in ['lower95','lower80','forecast','upper80','upper95']]
            assert lo95<=lo80<=fc<=hi80<=hi95
        if name=='Seasonal naive':close(r['forecast'],raw.loc[date-pd.DateOffset(years=1)])
    close(np.mean(np.abs(ee)),metrics[name]['MAE']);close(np.sqrt(np.mean(np.array(ee)**2)),metrics[name]['RMSE']);close(np.mean(ee),metrics[name]['Bias_actual_minus_forecast'])
    for h in [1,2,3]:
        e=[float(r['actual'])-float(r['forecast']) for r in group if int(r['horizon'])==h]
        assert len(e)==4;close(np.mean(np.abs(e)),hs[name,h]['MAE'])
# Validate the original models against the full-precision original reproduction record.
old=json.loads((ROOT/'results/original_reproduction.json').read_text())
for model in ['Seasonal naive','SARIMA']:
    for k in ['MAE','RMSE','Bias_actual_minus_forecast']:
        close(metrics[model][k],old['comparison'][model][k]['rerun'])
# Exercise actual growth and tie-selection functions without rerunning analysis.
tree=ast.parse((ROOT/'analysis.py').read_text());nodes=[]
for n in tree.body:
    if isinstance(n,ast.FunctionDef) and n.name in ['growth_adjustment','select_candidate']:nodes.append(n)
    if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='CANDIDATES' for t in n.targets):nodes.append(n)
ns={'np':np};exec(compile(ast.Module(body=nodes,type_ignores=[]),'<analysis_functions>','exec'),ns)
for cutoff in pd.to_datetime(['2024-12-01','2025-03-01','2025-06-01','2025-09-01']):
    history=raw.loc['2019-01-01':cutoff]
    result=ns['growth_adjustment'](history)
    changed=raw.copy();changed.loc[changed.index>cutoff]=1e9
    close(result,ns['growth_adjustment'](changed.loc['2019-01-01':cutoff]))
    vals={float(r['growth_adjustment_TWh']) for r in rows if r['Model']==models[1] and pd.Timestamp(r['origin'])==cutoff};assert len(vals)==1
# Same-differencing exact tie chooses AICc; cross-differencing tie retains enumeration.
assert ns['select_candidate'](pd.DataFrame({'candidate':[0,1],'MAE':[1.,1.],'initial_AICc':[10.,5.]}))==1
assert ns['select_candidate'](pd.DataFrame({'candidate':[1,4],'MAE':[1.,1.],'initial_AICc':[10.,5.]}))==1
assert ns['select_candidate'](pd.DataFrame({'candidate':[0,1],'MAE':[1.,1.00001],'initial_AICc':[10.,5.]}))==0
validation=read('validation_scores.csv');assert len({float(r['MAE']) for r in validation})==8
# Source inclusion does not alter recent-data naive rules.
for cutoff in pd.to_datetime(['2024-12-01','2025-03-01','2025-06-01','2025-09-01']):close(ns['growth_adjustment'](raw.loc[:cutoff]),ns['growth_adjustment'](raw.loc['2019-01-01':cutoff]))
sarima=[r for r in rows if r['Model']=='SARIMA']
assert sum(float(r['lower80'])<=float(r['actual'])<=float(r['upper80']) for r in sarima)==9
assert sum(float(r['lower95'])<=float(r['actual'])<=float(r['upper95']) for r in sarima)==10
import nbformat
nb=nbformat.read(ROOT/'electricity_project.ipynb',as_version=4);nbformat.validate(nb)
cells=[c for c in nb.cells if c.cell_type=='code'];assert len(cells)==7 and all(c.execution_count is not None for c in cells)
assert not any(o.output_type=='error' for c in cells for o in c.outputs)
# Sources of report/deck expose identical rounded metrics; no unresolved template markers.
for folder in ['report_ams_style','report','report_revised','presentation']:
    text=(ROOT/folder/'main.tex').read_text();assert '@@' not in text
    for name in models:
        for metric in ['MAE','RMSE']:
            assert f'{float(metrics[name][metric]):.3f}' in text
from pypdf import PdfReader
report=PdfReader(ROOT/'report_ams_style/main.pdf');deck=PdfReader(ROOT/'presentation/main.pdf')
assert len(deck.pages)==19
for reader in [report,deck]:
    text='\n'.join(p.extract_text() for p in reader.pages)
    for model in models:
        for metric in ['MAE','RMSE']:assert f'{float(metrics[model][metric]):.3f}' in text
assert '0.161' in '\n'.join(p.extract_text() for p in deck.pages[:12])
print('Verified hashes; original-score reproduction; 36 common forecasts; independent growth formula; cutoff invariance; tie handling; pooled/horizon metrics; coverage; notebook; report/deck values.')
print('SARIMA did not outperform growth-adjusted naive on 2025: MAE 0.343359 versus 0.161083 TWh.')
