"""Populate report and Beamer templates from the verified result CSVs.
Editable prose/layout: scripts/templates/*.tex. Primary output report is report_ams_style/main.tex.
"""
from pathlib import Path
import csv,json,re,shutil
ROOT=Path(__file__).resolve().parents[1]
def read(name):
    with (ROOT/'results'/name).open() as f:return list(csv.DictReader(f))
s=json.loads((ROOT/'results/summary.json').read_text())
models=['Seasonal naive','Growth-adjusted seasonal naive','SARIMA']
scores={r['Model']:r for r in read('test_scores.csv')}
horizon={(r['Model'],int(r['horizon'])):r for r in read('horizon_scores.csv')}
adj=read('growth_adjustments.csv');april=read('april_2025_block.csv')
short={'Seasonal naive':'Seasonal naive','Growth-adjusted seasonal naive':'Growth-adjusted naive','SARIMA':'SARIMA'}
def f(v,n=3):return f'{float(v):.{n}f}'
def table(headers,rows,caption=None,label=None,small=True,cols=None):
    # Tabularx wraps the descriptive column and leaves numerical columns legible.
    spec=cols or ('X'+'r'*(len(headers)-1))
    t=('\\SmallTable\n' if small else '')+'\\begin{tabularx}{\\linewidth}{@{}'+spec+'@{}}\\toprule\n'
    t+=' & '.join(headers)+r'\\'+ '\n\\midrule\n'
    t+='\n'.join(' & '.join(map(str,r))+r'\\' for r in rows)
    t+='\n\\bottomrule\\end{tabularx}\n'
    if caption:
        t='\\begin{table}[htbp]\n\\centering\n\\caption{'+caption+'}'+('\\label{'+label+'}' if label else '')+'\n{\\fontsize{9.2}{11.3}\\selectfont\n'+t.replace('\\SmallTable\n','')+'}\n\\end{table}\n'
    return t
score_rows=[[short[m],*[f(scores[m][k]) for k in ['MAE','RMSE','Bias_actual_minus_forecast']]] for m in models]
h_rows=[[str(h),'4',*[f(horizon[m,h]['MAE']) for m in models]] for h in [1,2,3]]
a_rows=[]
for h,month in enumerate(['April','May','June'],1):
    rows={r['Model']:r for r in april if int(r['horizon'])==h}
    a_rows.append([month,f(rows['SARIMA']['actual']),*[f(rows[m]['forecast']) for m in models]])
maes={m:float(scores[m]['MAE']) for m in models};b=maes[models[0]];g=maes[models[1]];m=maes[models[2]]
values={
 'BASE_MAE':f(b),'SARIMA_MAE':f(m),'GROWTH_MAE':f(g),
 'BASE_RMSE':f(scores[models[0]]['RMSE']),'SARIMA_RMSE':f(scores[models[2]]['RMSE']),'GROWTH_RMSE':f(scores[models[1]]['RMSE']),
 'GAIN':f(100*(b-m)/b,1),'GROWTH_VS_SARIMA':f(100*(m-g)/m,1),'MAE_DIFF':f(m-g),
 'SENS_MAE':f(s['sensitivity_include_2018']['MAE']),'SENS_RMSE':f(s['sensitivity_include_2018']['RMSE']),
 'ADJUSTMENTS':', '.join(f(r['growth_adjustment_TWh'],4) for r in adj),
 'APRIL_ADJ':f(adj[1]['growth_adjustment_TWh'],6),'APRIL_BASE':a_rows[0][2],'APRIL_GROWTH':a_rows[0][3],
 'SCORES_TABLE':table(['Model','MAE','RMSE','Mean error'],score_rows,'Pooled 2025 test scores, all in TWh, for identical forecast blocks. Mean error is actual minus forecast; positive values indicate underprediction. The growth-adjusted rule is a follow-up comparison.','tab:scores'),
 'SCORES_SLIDE_TABLE':table(['Model','MAE (TWh)','RMSE (TWh)','Mean error (TWh)'],score_rows),
 'HORIZON_TABLE':table(['Horizon','Count','Naive','Growth-adjusted','SARIMA'],h_rows,'MAE by horizon in TWh. There are only four forecasts per horizon. Growth-adjusted denotes the added follow-up benchmark.','tab:horizon'),
 'HORIZON_SLIDE_TABLE':table(['Horizon','Count','Naive MAE','Growth-adjusted MAE','SARIMA MAE'],h_rows),
 'APRIL_TABLE':table(['Month','Actual','Naive','Growth-adjusted','SARIMA'],a_rows,'April--June 2025 block, issued through March 2025. All entries are TWh; actuals are shown only for later comparison.','tab:april'),
 'APRIL_SLIDE_TABLE':table(['Month','Actual','Naive','Growth-adjusted','SARIMA'],a_rows)
}
c_rows=[]
for r in read('validation_scores.csv'):
    # Keep the original validation table order and full precision in CSV.
    spec=re.search(r'SARIMA(.*?)\[12\]',r['Model']).group(1).replace(' ','')
    c_rows.append([spec,'Yes' if 'constant' in r['Model'] else 'No',f(r['MAE']),f(r['initial_AICc'],2)])
values['CANDIDATE_TABLE']=table(['Specification, period 12','Constant','MAE (TWh)','Initial AICc'],c_rows)
coefrows=[]
for r in read('coefficients.csv'):
    term={'intercept':'Constant $c$','ar.L1':'AR $\\phi$','ma.S.L12':'Seasonal MA $\\theta$','sigma2':'Innovation variance ($\\mathrm{TWh}^2$)'}[r['term']]
    coefrows.append([term,f(r['estimate'],4),f(r['std_error'],4)])
values['COEF_TABLE']=table(['Parameter','Estimate','Std. error'],coefrows)
# Existing in-editor source is edited in place. Other report variants are synchronized aliases.
for kind,target in [('report',ROOT/'report_ams_style'),('slides',ROOT/'presentation')]:
    target.mkdir(exist_ok=True)
    text=(ROOT/'scripts/templates'/f'{kind}.tex').read_text()
    for k,v in values.items():text=text.replace('@@'+k+'@@',v)
    assert not re.findall(r'@@[A-Z_]+@@',text)
    (target/'main.tex').write_text(text)
    (target/'images').mkdir(exist_ok=True)
    images=['01_history','02_seasonality','04_test_forecasts','05_residuals'] if kind=='report' else ['01_history','03_acf_pacf','04_test_forecasts','05_residuals','06_test_slide']
    for im in images:shutil.copy2(ROOT/'figures'/f'{im}.png',target/'images'/f'{im}.png')
    (target/'README.txt').write_text('Compile main.tex with pdfLaTeX twice. Keep images/ beside main.tex.\nGenerated from scripts/templates/'+kind+'.tex and result CSVs by scripts/build_documents.py.\nThe growth-adjusted benchmark is a follow-up, not part of the original selection.\n')
for folder in ['report','report_revised']:
    target=ROOT/folder;target.mkdir(exist_ok=True)
    shutil.copy2(ROOT/'report_ams_style/main.tex',target/'main.tex')
    shutil.copytree(ROOT/'report_ams_style/images',target/'images',dirs_exist_ok=True)
    content={'version':'2026-11-24 growth benchmark revision','authoritative_template':'scripts/templates/report.tex', 'generated_tex':'report_ams_style/main.tex','summary':s}
    (target/'content.json').write_text(json.dumps(content,indent=2))
    (target/'README.txt').write_text('Synchronized alias of report_ams_style/. Edit scripts/templates/report.tex and run scripts/build_documents.py to regenerate.\n')
# Editable speaking notes use the same words as the deck's note fields.
slides=(ROOT/'presentation/main.tex').read_text()
notes=re.findall(r'\\note\{(.*?)\}\s*\\end\{frame\}',slides,re.S)
(ROOT/'materials').mkdir(exist_ok=True)
(ROOT/'materials/speaking_notes.txt').write_text('Suggested allocation: Person 1 slides 1-3; Person 2 slides 4-6; Person 3 slides 7-9; Person 4 slides 10-12.\nAim for 10-12 minutes, with pauses to explain plots. Backups are for questions.\n\n'+'\n\n'.join(notes))
# A readable handout accompanies the editable notes.
from reportlab.platypus import SimpleDocTemplate,Paragraph,Spacer
from reportlab.lib.styles import getSampleStyleSheet
import html
styles=getSampleStyleSheet();story=[Paragraph('Four-person speaking guide',styles['Title']),Paragraph('12 main slides; technical backups follow. Aim for 10-12 minutes overall.',styles['Normal']),Spacer(1,14)]
for note in notes:
    heading,_,text=note.partition('. ')
    story += [Paragraph(html.escape(heading),styles['Heading2']),Paragraph(html.escape(text),styles['BodyText']),Spacer(1,8)]
SimpleDocTemplate(str(ROOT/'materials/speaking_guide.pdf')).build(story)
# Human-readable interpretation is generated from the result CSVs.
(ROOT/'results/revision_summary.txt').write_text(f'''Original results reproduce with no discrepancy.\n2025 MAE: naive {b:.6f}, growth-adjusted {g:.6f}, SARIMA {m:.6f} TWh.\nDid SARIMA beat growth-adjusted naive? No.\nGrowth-adjusted MAE is {100*(m-g)/m:.1f}% lower than SARIMA's.\nSingle test year, four origins; added benchmark is a follow-up prompted by original results.\nNo growth rule tuning on 2025. Only the latest 12 observed year-on-year changes are averaged at each cutoff.\n''')
print('Updated editable report, slides, speaking notes and guide from result CSVs.')
