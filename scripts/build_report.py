from pathlib import Path
import json, csv, sys, html, zipfile
ROOT=Path(__file__).resolve().parent.parent
OUT=ROOT
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image, PageBreak, KeepTogether
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import cm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
# Optional Times New Roman fonts. Core PDF Times fonts provide a portable fallback.
import os
FONT_DIR=Path(os.environ.get('REPORT_FONT_DIR','/System/Library/Fonts/Supplemental'))
FONT_FILES=[('Academic-Roman','Times New Roman.ttf'),('Academic-Bold','Times New Roman Bold.ttf'),
            ('Academic-Italic','Times New Roman Italic.ttf'),('Academic-BoldItalic','Times New Roman Bold Italic.ttf')]
EMBED_FONTS=all((FONT_DIR/f).is_file() for _,f in FONT_FILES)
if EMBED_FONTS:
    for alias,filename in FONT_FILES:
        pdfmetrics.registerFont(TTFont(alias,str(FONT_DIR/filename)))
    pdfmetrics.registerFontFamily('Academic-Roman',normal='Academic-Roman',bold='Academic-Bold',italic='Academic-Italic',boldItalic='Academic-BoldItalic')
from pypdf import PdfReader
S=json.loads((OUT/'results/summary.json').read_text())
B,M=S['test']
G=S['mae_improvement_percent']
sens=S['sensitivity_include_2018']
W,H=A4
CW=W-4*cm
styles=getSampleStyleSheet()
styles.add(ParagraphStyle(name='ReportTitle',fontName='Academic-Bold',fontSize=18,leading=21,alignment=TA_CENTER,spaceAfter=9))
styles.add(ParagraphStyle(name='ReportMeta',fontName='Academic-Roman',fontSize=10,leading=13,alignment=TA_CENTER,spaceAfter=12))
styles.add(ParagraphStyle(name='BodyAcademic',fontName='Academic-Roman',fontSize=10.8,leading=14.1,alignment=TA_JUSTIFY,spaceAfter=8))
styles.add(ParagraphStyle(name='SectionAcademic',fontName='Academic-Bold',fontSize=12.5,leading=16,spaceBefore=9,spaceAfter=7))
styles.add(ParagraphStyle(name='SubAcademic',fontName='Academic-Bold',fontSize=11,leading=14,spaceBefore=7,spaceAfter=5))
styles.add(ParagraphStyle(name='CaptionAcademic',fontName='Academic-Roman',fontSize=9,leading=11.5,spaceAfter=8))
styles.add(ParagraphStyle(name='SmallAcademic',fontName='Academic-Roman',fontSize=9.1,leading=12,spaceAfter=6))
styles.add(ParagraphStyle(name='EquationAcademic',fontName='Academic-Italic',fontSize=11,leading=18,alignment=TA_CENTER,spaceAfter=6))
styles.add(ParagraphStyle(name='TableAcademic',fontName='Academic-Roman',fontSize=9.3,leading=11.5))
styles.add(ParagraphStyle(name='GuideTitle',fontName='Academic-Bold',fontSize=19,leading=23,spaceAfter=14))
styles.add(ParagraphStyle(name='GuideBody',fontName='Academic-Roman',fontSize=11.2,leading=16,spaceAfter=11))
# Captured report content is also the input to the LaTeX renderer.
if not EMBED_FONTS:
    for name in ['ReportTitle','ReportMeta','BodyAcademic','SectionAcademic','SubAcademic','CaptionAcademic','SmallAcademic','EquationAcademic','TableAcademic','GuideTitle','GuideBody']:
        styles[name].fontName={'Academic-Roman':'Times-Roman','Academic-Bold':'Times-Bold','Academic-Italic':'Times-Italic'}.get(styles[name].fontName,styles[name].fontName)
story=[]; source_text=[]; report_events=[]
def p(text,sty='BodyAcademic',target=None):
    (story if target is None else target).append(Paragraph(text,styles[sty]))
    if target is None:
        source_text.append(text)
        report_events.append({'type':'paragraph','style':sty,'text':text})
def section(t): p(t,'SectionAcademic')
def eq(t): p(t,'EquationAcademic')
def cap(t): p(t,'CaptionAcademic')
def table(rows,widths=None,target=None):
    if target is None: report_events.append({'type':'table','rows':rows,'widths':widths})
    converted=[[Paragraph(str(v),styles['TableAcademic']) for v in row] for row in rows]
    t=Table(converted,colWidths=widths or [CW/len(rows[0])]*len(rows[0]),hAlign='CENTER')
    t.setStyle(TableStyle([('VALIGN',(0,0),(-1,-1),'TOP'),('TOPPADDING',(0,0),(-1,-1),5),
        ('BOTTOMPADDING',(0,0),(-1,-1),5),('LINEABOVE',(0,0),(-1,0),.7,colors.black),
        ('LINEBELOW',(0,0),(-1,0),.5,colors.black),('LINEBELOW',(0,-1),(-1,-1),.7,colors.black),
        ('BACKGROUND',(0,0),(-1,0),colors.HexColor('#f0f0f0'))]))
    (story if target is None else target).extend([t,Spacer(1,7)])
def fig(name,height):
    report_events.append({'type':'figure','filename':name,'height_cm':height/cm})
    img=Image(str(OUT/'figures'/name))
    ratio=img.imageHeight/img.imageWidth
    img.drawWidth=min(CW,height/ratio); img.drawHeight=img.drawWidth*ratio
    img.hAlign='CENTER'; story.append(img)
def page():
    story.append(PageBreak()); source_text.append('\n[PAGE BREAK]\n')
    report_events.append({'type':'pagebreak'})
def footer(canvas,doc):
    canvas.setFont('Academic-Roman' if EMBED_FONTS else 'Times-Roman',9)
    canvas.drawCentredString(W/2,1.12*cm,str(doc.page))
def make_pdf(path,parts):
    SimpleDocTemplate(str(path),pagesize=A4,rightMargin=2*cm,leftMargin=2*cm,topMargin=1.6*cm,
        bottomMargin=1.65*cm,title='Forecasting Kazakhstan electricity generation',author='Mathematics project group, Nazarbayev University').build(parts,onFirstPage=footer,onLaterPages=footer)

# Page 1: academic title, abstract, introduction, source audit.
p('FORECASTING KAZAKHSTAN\'S TOTAL MONTHLY<br/>ELECTRICITY GENERATION USING SARIMA','ReportTitle')
p('Mathematics project group<br/>Nazarbayev University<br/>Time Series Final Project - 22 November 2026','ReportMeta')
p(f'<b>Abstract.</b> This study compares a seasonal naive baseline with SARIMA for forecasting Kazakhstan\'s national monthly electricity generation. A frozen Ember dataset contains 102 months, while the main experiment uses 84 observations from 2019 to 2025 after a source audit. Eight low-order specifications are compared using 2024 validation forecasts. SARIMA(1,0,0)(0,1,1)<sub>12</sub> with a constant achieves a 2025 test MAE of {M["MAE"]:.3f} TWh, compared with {B["MAE"]:.3f} TWh for the baseline, a {G:.1f}% reduction. Residual tests reveal no significant autocorrelation at the examined lags. However, prediction intervals under-cover this small test sample, and source construction limits interpretation.')
section('1. Introduction')
p('National electricity generation provides a clear application for seasonal time-series forecasting. Short-term forecasts can inform discussion of expected production, although they do not by themselves determine dispatch, consumption or infrastructure requirements. This project asks: <i>Does SARIMA improve three-month forecasts of Kazakhstan\'s monthly electricity generation relative to using the same months from the previous year?</i>')
p('The scope is deliberately univariate. The study compares a transparent seasonal benchmark with a small classical model, using the same forecast origins and horizons. The study evaluates whether short-term dependence and a seasonal difference add useful predictive information beyond repeating last year. A source check and a sensitivity analysis support interpretation of the resulting comparison.')
section('2. Data description and quality')
p('Ember\'s public monthly electricity file [1] is filtered to <i>Area = Kazakhstan</i> and <i>Electricity source = Total generation</i>. The target is <i>Generation (TWh)</i>, measured in terawatt-hours. One TWh equals one billion kWh. Dates identify months. The dataset covers the national total, not only Samruk-Energy\'s own plants.')
table([['Snapshot audit','Verified result'],['Coverage','January 2018-June 2026; 102 months'],['Missingness','No missing months, blank targets or duplicate dates'],['Main experiment','January 2019-December 2025; 84 months'],['Snapshot downloaded','18 November 2026; preserved as a local CSV']],widths=[CW*.32,CW*.68])
cap('Table 1. Audit of the unchanged national series. The current study uses a frozen data version.')
page()

# Page 2: audit qualification and exploration.
section('2.1. Source discrepancy and sample choice')
p('The absence of blank cells does not establish measurement quality. Ember lists 9.780 TWh for each of January-March 2018. Samruk\'s original January report [3] gives 10,357.3 million kWh, or 10.3573 TWh. Its first-quarter report gives 29.3392 TWh, close to Ember\'s three-month sum of 29.340 TWh. This is consistent with quarterly averaging, but does not prove how the whole file was constructed. The main experiment excludes 2018, keeps the original values unchanged, and checks sensitivity to adding that year back. The partial 2026 year is outside the main experiment so that validation and testing use complete calendar years.')
section('2.2. Time-series patterns')
fig('01_history.png',5.25*cm)
cap('Figure 1. Main study series. Shaded regions mark the validation and test years. The historical display includes all study years, while model exploration uses only 2019-2023.')
fig('02_seasonality.png',5.1*cm)
cap('Figure 2. Monthly patterns in the initial training sample. Higher winter values and lower summer values suggest an annual seasonal component. The plot does not establish a causal weather effect.')
p(f'The training-set lag-12 autocorrelation is {S["initial_training_seasonal_acf12"]:.3f}. The ADF test on levels has p = 0.186, while the level-stationarity KPSS test has p &gt;= 0.10. These results alone are inconclusive. After seasonal differencing, the ADF p-value is 0.0008 and the KPSS p-value is 0.095. Together with the plots, this supports considering a seasonal difference. ADF uses a constant, AIC lag selection and maximum lag 8. KPSS uses a constant and automatic bandwidth. Table-limit p-values are bounds.')
page()

# Page 3: model and evaluation, candidate table.
section('3. Methodology')
p('Let y<sub>t</sub> denote monthly national generation. The seasonal naive forecast repeats last year\'s matching month. For horizons h = 1, 2, 3 at forecast origin T:')
eq('y-hat<sub>T+h|T</sub> = y<sub>T+h-12</sub>. &nbsp;&nbsp; (1)')
p('SARIMA(p,d,q)(P,D,Q)<sub>12</sub> combines ordinary and seasonal autoregressive, differencing and moving-average components [4]. Parameters use state-space maximum likelihood in statsmodels [5], with stationary AR and invertible MA constraints. For the selected model, define z<sub>t</sub> = y<sub>t</sub> - y<sub>t-12</sub>. Then:')
eq('z<sub>t</sub> = c + phi z<sub>t-1</sub> + e<sub>t</sub> + theta e<sub>t-12</sub>. &nbsp;&nbsp; (2)')
p('The innovations e<sub>t</sub> have mean zero and constant variance under the model. The constant permits an average year-on-year change. No logarithm, external regressor or machine-learning model is used. Eight candidates are fixed before test scoring. The smallest 2024 validation MAE selects the order, with initial-training AICc as a tie-breaker. AICc is not the forecast accuracy measure. Every numerical fit converged.')
table([['Stage','Dates','Observations'],['Initial training','January 2019-December 2023','60'],['Validation / order selection','January-December 2024','12'],['Held-out test','January-December 2025','12']],widths=[CW*.34,CW*.47,CW*.19])
cap('Table 2. Chronological design. Each validation and test year contains four non-overlapping three-month blocks.')
p('Before January, April, July and October, each approach uses observations only through the preceding month. Parameters are refitted on the expanding history, but the selected SARIMA order stays fixed during testing. No actual values from within a three-month block enter that block\'s forecasts. Earlier observed blocks may enter subsequent fits. Thus horizons 1, 2 and 3 are identical across models. MAE = mean(|y - y-hat|), and RMSE = sqrt(mean((y - y-hat)<super>2</super>)); both are in TWh.')
rows=[['SARIMA specification','Constant','Validation MAE','Initial AICc']]
for r in S['validation']:
    i=r['candidate']; pairs=[('(1,0,0)(1,1,0)','Yes'),('(1,0,0)(0,1,1)','Yes'),('(0,0,1)(0,1,1)','Yes'),('(1,0,1)(0,1,1)','Yes'),('(0,1,1)(0,1,1)','No'),('(1,1,0)(0,1,1)','No'),('(0,1,1)(1,1,0)','No'),('(1,1,0)(1,1,0)','No')]
    a,b=pairs[i]; rows.append([a,b,f'{r["MAE"]:.3f}',f'{r["initial_AICc"]:.2f}'])
table(rows,widths=[CW*.41,CW*.15,CW*.22,CW*.22])
cap('Table 3. Candidate comparison, seasonal period 12 throughout. Seasonal naive validation MAE is 0.508 TWh. AICc values across different differencing orders are descriptive only, not used for cross-order selection.')
page()

# Page 4: real forecast performance.
section('4. Out-of-sample results')
p(f'The selected SARIMA(1,0,0)(0,1,1)<sub>12</sub> with a constant yields validation MAE 0.354 TWh. Its specification is then frozen for testing. Across 12 held-out observations in 2025, MAE falls from {B["MAE"]:.3f} to {M["MAE"]:.3f} TWh, a reduction of {G:.1f}%. RMSE falls from {B["RMSE"]:.3f} to {M["RMSE"]:.3f} TWh. These are descriptive improvements for one test year, not a formal finding of universal or statistically significant superiority.')
table([['Model','MAE (TWh)','RMSE (TWh)','Mean error (TWh)'],['Seasonal naive',f'{B["MAE"]:.3f}',f'{B["RMSE"]:.3f}',f'{B["Bias_actual_minus_forecast"]:.3f}'],['Selected SARIMA',f'{M["MAE"]:.3f}',f'{M["RMSE"]:.3f}',f'{M["Bias_actual_minus_forecast"]:.3f}']],widths=[CW*.32,CW*.22,CW*.22,CW*.24])
cap('Table 4. Test scores for the same four three-month forecast blocks. Mean error is actual minus forecast, so positive values indicate underprediction.')
fig('04_test_forecasts.png',7.0*cm)
cap('Figure 3. Actual and predicted generation in 2025. Shading shows nominal Gaussian SARIMA prediction intervals. Vertical lines separate blocks with newly fitted parameters. Lines connect forecasts from different origins for readability.')
rows=[['Horizon','Observations','Baseline MAE','SARIMA MAE']]
with open(OUT/'results/horizon_scores.csv') as f: hs=list(csv.DictReader(f))
for h in [1,2,3]:
    b=next(r for r in hs if r['Model']=='Seasonal naive' and int(r['horizon'])==h)
    m=next(r for r in hs if r['Model']=='SARIMA' and int(r['horizon'])==h)
    rows.append([f'{h} month(s)','4',f'{float(b["MAE"]):.3f}',f'{float(m["MAE"]):.3f}'])
table(rows)
cap('Table 5. Error by horizon, in TWh. With only four observations per horizon, differences are sensitive to individual months.')
p('Both models underpredict on average. Every 2025 monthly total exceeds its 2024 counterpart, which puts the seasonal naive rule at a disadvantage. SARIMA partially adapts to increasing levels, but does not eliminate the bias. The third-month errors remain relatively large. This pattern supports cautious use of a short horizon.')
page()

# Page 5: diagnostics and parameter uncertainty.
section('5. Model estimates and diagnostics')
p('For a diagnostic view uncontaminated by test observations, the selected specification is fitted through December 2024. Table 6 reports maximum-likelihood estimates and their asymptotic standard errors. These estimates are not the coefficients from every quarterly refit. The seasonal MA estimate is relatively uncertain, which is consistent with the limited number of annual cycles.')
rows=[['Parameter','Estimate','Standard error']]
names={'intercept':'Constant c','ar.L1':'AR coefficient phi','ma.S.L12':'Seasonal MA theta','sigma2':'Innovation variance (TWh squared)'}
for r in S['coefficients']: rows.append([names[r['term']],f'{r["estimate"]:.4f}',f'{r["std_error"]:.4f}'])
table(rows,widths=[CW*.52,CW*.24,CW*.24])
cap('Table 6. Pre-test fit using January 2019-December 2024. In equation (2), c is the intercept of z, not its unconditional mean.')
fig('05_residuals.png',7.7*cm)
cap('Figure 4. Residual sequence and autocorrelation from the pre-test fit. The first 13 residuals are omitted to reduce initialization effects. Remaining residual mean = 0.016 TWh. ACF bounds are approximate individual-lag reference bounds.')
p('Ljung-Box statistics are 8.075 at lag 12 (p = 0.621) and 18.888 at lag 24 (p = 0.652), adjusting degrees of freedom for two AR/MA coefficients. The tests do not reject the absence of residual autocorrelation at these lags. This does not prove independence, normality, constant variance or correct specification. The residual plot and seasonal-source limitations remain relevant.')
p('The SARIMA 80% intervals contain 9 of 12 test observations (75.0%), and its 95% intervals contain 10 of 12 (83.3%). These are nominal Gaussian intervals conditional on the fitted model and estimated parameters. They do not fully reflect parameter uncertainty or data revisions. Coverage below the nominal levels is an important limitation, even though point-forecast errors improve. Twelve observations cannot precisely assess long-run coverage.')
page()

# Page 6: robustness, a dated forecast, limitations and concise references.
section('6. Sensitivity, limitations and conclusion')
p(f'Adding 2018 back while retaining the selected SARIMA order gives test MAE {sens["MAE"]:.3f} TWh and RMSE {sens["RMSE"]:.3f} TWh. The seasonal naive forecasts are unchanged because their matching months lie in 2024. The SARIMA advantage therefore remains, although its magnitude is smaller. This is a sensitivity check, not another model-selection round.')
p('The analysis uses a current frozen snapshot, not the data vintages available at each historical forecast origin. Later revisions or source construction may affect past values. Other repeated observations remain after 2018, and only a small part of the source chain was independently checked. Forecasts should therefore be interpreted as forecasts of the published Ember series, not as independently validated measurements of physical generation.')
p('A single held-out year and four forecast origins limit generalization. The univariate model does not explain weather, plant outages, fuel supply, trade or policy changes. Monthly totals also reflect unequal month lengths. Generation is not the same as demand, and successful historical forecasts do not establish a causal relationship or an operational planning rule.')
p('For illustration, a refit through December 2025 produces the following three-month forecasts. These use only the study endpoint and are deliberately dated. They are not live forecasts made from November 2026 and are not part of the model-selection or main test scores.')
rows=[['Forecast month','Forecast (TWh)','95% lower','95% upper']]
with open(OUT/'results/dated_forecast_illustration.csv') as f:
    for r in csv.DictReader(f): rows.append([r['Date'][:7],f'{float(r["forecast"]):.3f}',f'{float(r["lower95"]):.3f}',f'{float(r["upper95"]):.3f}'])
table(rows)
cap('Table 7. Dated forecast illustration, conditional on observations through December 2025.')
p(f'<b>Conclusion.</b> For this historical evaluation, SARIMA improves three-month point forecasts over the seasonal naive rule, reducing test MAE by {G:.1f}%. The benefit persists when 2018 is included. Residual autocorrelation tests do not reveal a clear remaining pattern, but the interval coverage and source audit prevent a stronger reliability claim. A longer evaluation across more forecast origins and better-verified monthly source data would be the most useful next steps.')
section('References')
refs=[
('[1] Ember. Monthly Electricity Data. Snapshot downloaded 18 November 2026.','https://ember-energy.org/data/monthly-electricity-data/'),
('[2] Ember. Electricity Data Methodology, version 1.6. Kazakhstan source notes.','https://files.ember-energy.org/public-downloads/ember_electricity_data_methodology.pdf'),
('[3] Samruk-Energy. Electricity market reports, January and January-March 2018.','https://samruk-energy.kz/en/press-center/analytical-review'),
('[4] Hyndman, R. J. and Athanasopoulos, G. (2021). Forecasting: Principles and Practice, 3rd ed. OTexts. Chapters 5 and 9.','https://otexts.com/fpp3/'),
('[5] statsmodels. SARIMAX documentation, version 0.15.0.','https://www.statsmodels.org/stable/generated/statsmodels.tsa.statespace.sarimax.SARIMAX.html')]
for t,url in refs: p(html.escape(t)+' <link href="'+url+'" color="#194c76">'+html.escape(url)+'</link>','SmallAcademic')
make_pdf(OUT/'report/project_report.pdf',story)
(OUT/'report/report_text.txt').write_text('\n\n'.join(source_text))
(OUT/'report/content.json').write_text(json.dumps(report_events,indent=2))
print('Report pages:',len(PdfReader(OUT/'report/project_report.pdf').pages))

# Separate preparation guide: no slides are produced.
guide=[]
def gp(t,sty='GuideBody'):
    p(t,sty,target=guide)
    if sty=='GuideTitle': guide.append(Spacer(1,8))
def gpage(): guide.append(PageBreak())
gp('Speaking guide and group roles','GuideTitle')
gp('Forecasting Kazakhstan\'s Total Monthly Electricity Generation Using SARIMA','ReportMeta')
gp('Use this guide to understand the report and rehearse. A four-person explanation takes approximately 8-10 minutes, depending on speaking speed and pauses. Timing is an assumption until the professor specifies the oral format. No slide deck is included.')
table([['Person','Report responsibility','Concrete deliverable'],['1','Introduction and data audit','Explain the target, source, exclusions and data-quality check'],['2','Exploration and evaluation design','Explain seasonality, the baseline and chronological testing'],['3','SARIMA and diagnostics','Explain the selected equation and residual checks'],['4','Results and limitations','Explain the error table, interval coverage and conclusion']],widths=[CW*.12,CW*.36,CW*.52],target=guide)
gp('Recommended preparation','SectionAcademic')
gp('First, read your report section with its corresponding notebook output. Check that you can explain each number in ordinary language. Then read the next person\'s section so the transitions make sense. Rehearse aloud with the actual report figures, time each person, and shorten explanations before increasing speaking speed.')
gp('Shared facts everyone should know','SectionAcademic')
gp('The full snapshot has 102 months, but the main study has 84. We use 2019-2023 for initial training, 2024 for validation and 2025 for testing. We forecast three months at a time. SARIMA reduces test MAE from 0.435 to 0.343 TWh. The main claim concerns a small historical experiment, not guaranteed future performance.')
gp('Assign the four roles to your group members and add author names to your submission in the format required by the professor. The supplied examples guide the style; an official rubric still takes precedence.')
gpage()
scripts=[
('Person 1: motivation and data',[
'Our project forecasts Kazakhstan\'s total monthly electricity generation. We study the national total, rather than one company or region, and measure generation in terawatt-hours. One terawatt-hour is one billion kilowatt-hours. Our question is whether a seasonal ARIMA model can predict the next three months more accurately than using the same months from last year.',
'We use public data from Ember, whose methodology identifies Samruk as a source for Kazakhstan\'s monthly generation. The downloaded snapshot contains 102 consecutive months from January 2018 to June 2026. It has no missing months, blank national values or duplicate dates. However, complete data can still contain quality problems.',
'We found that Ember assigns exactly 9.780 terawatt-hours to each of the first three months of 2018. The original Samruk January report gives 10.3573. The first-quarter total is close to the sum of Ember\'s repeated values, which suggests averaging may have occurred. We do not claim to have established how every observation was constructed.',
'For that reason, our main analysis excludes 2018. It uses the 84 monthly observations from 2019 through 2025, with complete calendar years for validation and testing. We keep the source values unchanged and later check whether including 2018 changes our conclusion. The next section explains the seasonal pattern and our evaluation design.'
]),
('Person 2: patterns, baseline and evaluation',[
'The training-data seasonal plot shows higher generation in winter and lower values in summer. This suggests a pattern repeating every twelve months. It motivates a seasonal model, although the plot alone cannot prove that temperature causes the pattern. We use monthly totals, so month length can also affect the values.',
'Our baseline is seasonal naive. To forecast January, for example, it simply uses the previous January\'s generation. This rule is easy to understand and gives the statistical model a meaningful benchmark. A complex model is useful only if it improves on something simple.',
'We preserve the order of time. The first sixty observations, covering 2019 to 2023, form the initial training set. We use the twelve observations in 2024 to choose among eight small SARIMA specifications. We reserve 2025 for the final comparison and do not use its errors to choose the model.',
'In each evaluation year, we forecast January to March, then April to June, July to September and October to December. At each boundary, we refit using only the observations already available. We never use actual values from inside a forecast block to predict another month in that same block. Both methods therefore predict the same three months from the same information.',
'We measure accuracy using mean absolute error and root mean squared error, both in terawatt-hours. MAE gives the average absolute miss, while RMSE gives more weight to large misses. We also report errors separately for the first, second and third forecast months.'
]),
('Person 3: SARIMA and residual checks',[
'SARIMA extends ARIMA by including relationships that repeat over a seasonal period. Here that period is twelve months. Our selected model is SARIMA one-zero-zero, zero-one-one, with a period of twelve and a constant. It has one ordinary autoregressive term, one seasonal difference and one seasonal moving-average term.',
'To interpret the equation, we first subtract the value from twelve months earlier. This gives the year-on-year change, which we call z. The model relates this change to the previous month\'s change, a constant, the current unpredictable innovation and an innovation from twelve months earlier. The constant lets the model accommodate an average annual change.',
'We select this specification because it has the lowest validation MAE among the eight candidates. We estimate parameters by maximum likelihood and keep the order fixed during testing. The code uses a class called SARIMAX, but we supply no external variables, so it implements a SARIMA model.',
'We then examine residuals from a fit using observations only through December 2024. Residuals are actual values minus fitted values. If large systematic patterns remain, the model has missed useful information. We omit the first thirteen residuals to reduce initialization effects.',
'The Ljung-Box p-values are about 0.62 at lag twelve and 0.65 at lag twenty-four. We therefore do not detect significant residual autocorrelation at those examined lags. This does not prove that the model is correct or that its uncertainty intervals are reliable. The final section shows the held-out forecast results and their limitations.'
]),
('Person 4: findings and conclusion',[
f'On the 2025 test year, the seasonal naive baseline has mean absolute error of {B["MAE"]:.3f} terawatt-hours. SARIMA reduces this to {M["MAE"]:.3f}. That is about a {G:.0f} percent reduction in average absolute forecast error. RMSE also falls, from {B["RMSE"]:.3f} to {M["RMSE"]:.3f} terawatt-hours. We calculate these scores using the same twelve actual observations and the same forecast blocks.',
'Both approaches underpredict on average. Every month in 2025 has higher generation than its matching month in 2024. This disadvantages the baseline, which simply repeats last year. SARIMA adapts to some of the increase, although its third-month forecasts still have larger errors than its earlier horizons.',
'We also test sensitivity to the disputed early data. Adding 2018 back, without choosing a different model, gives SARIMA MAE of about 0.360 terawatt-hours. It remains below the baseline, so the direction of the conclusion is unchanged.',
'The uncertainty intervals deserve caution. The nominal ninety-five percent SARIMA intervals contain only ten of the twelve test observations. The nominal eighty percent intervals contain nine. These results show that better point forecasts do not automatically mean well-calibrated uncertainty. With twelve test values, our assessment is also imprecise.',
'Our conclusion is that SARIMA improves point forecasts in this historical experiment. We cannot promise the same improvement in another year. The source discrepancy, later revisions, limited test sample and omitted factors such as weather and outages remain important limitations. The dated early-2026 forecast in the report is an illustration, not a current forecast made in November.'
])]
for title,paras in scripts:
    gp(title,'GuideTitle')
    for para in paras: gp(html.escape(para))
    gp('Your concrete preparation task','SectionAcademic')
    task={'Person 1':'Locate the source discrepancy in the audit JSON and explain why missing-value checks alone are insufficient.',
          'Person 2':'Trace one forecast block in test_predictions.csv and show that its origin precedes every target month.',
          'Person 3':'Explain equation (2) and identify the AR and seasonal MA estimates in Table 6.',
          'Person 4':'Recalculate the percentage MAE reduction from Table 4 and explain why 10/12 coverage is a limitation.'}[title.split(':')[0]]
    gp(task)
    gpage()
gp('Questions to practise together','GuideTitle')
qa=[
('Why choose electricity?','It gives a local application, regular monthly data and several annual cycles. It supports a simple seasonal comparison without collecting external predictors.'),
('What is the difference between generation and demand?','Generation is electricity produced. Demand is a different quantity and can involve net imports and other accounting definitions. We forecast the published generation series only.'),
('Why do 102 observations become 84?','We exclude twelve months in 2018 following the source discrepancy, and the six available months of the partial 2026 year. This leaves 2019-2025.'),
('Why not use all data for training?','Then there would be no unseen observations for evaluating forecast accuracy. Validation selects settings; the test year assesses the frozen modelling rule.'),
('What does seasonal differencing do?','It subtracts each value from its matching month one year earlier. It can remove a repeating annual seasonal level.'),
('Why is d zero but D one?','Lowercase d is ordinary differencing. Uppercase D is seasonal differencing. The selected model uses one seasonal difference and no additional ordinary difference.'),
('Is the constant c the average annual change?','Not directly. In the selected AR(1) equation for the seasonal difference, its stationary mean is c divided by one minus phi.'),
('Does a high Ljung-Box p-value prove a good model?','No. It means these tests did not detect residual autocorrelation at the selected lags. It does not establish normality, independence or accurate prediction intervals.'),
('Does 21% improvement mean 79% accuracy?','No. It is a relative reduction in MAE: 100 times baseline MAE minus model MAE, divided by baseline MAE. It is not an accuracy percentage.'),
('What if the professor asks for a real future forecast?','The snapshot ends in June 2026. Update and audit the source, then refit with information available at the new origin. Do not label the dated January-March illustration as a current forecast.')]
for q,a in qa:
    gp(html.escape(q),'SubAcademic'); gp(html.escape(a),'SmallAcademic')
make_pdf(OUT/'materials/speaking_guide.pdf',guide)
plain=['Speaking guide and roles','No slide deck has been created.']
for title,paras in scripts: plain.extend([title,*paras])
plain.extend(['Questions and answers',*[q+'\n'+a for q,a in qa]])
(OUT/'materials/speaking_notes.txt').write_text('\n\n'.join(plain))

print('Guide pages:',len(PdfReader(OUT/'materials/speaking_guide.pdf').pages))
