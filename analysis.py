# %%
"""Kazakhstan electricity project. Run this file or the matching notebook.
Data are a frozen Ember snapshot downloaded on 2026-11-18.
"""
from pathlib import Path
import sys, os, json, warnings, hashlib, platform
BASE = Path(__file__).resolve().parent if '__file__' in globals() else Path.cwd()
if not (BASE / 'data').exists():
    BASE = BASE / 'outputs'
os.environ.setdefault('MPLCONFIGDIR', str(BASE / '.cache' / 'matplotlib'))
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import statsmodels
from statsmodels.tsa.statespace.sarimax import SARIMAX
from statsmodels.tsa.stattools import adfuller, kpss, acf
from statsmodels.stats.diagnostic import acorr_ljungbox
from statsmodels.graphics.tsaplots import plot_acf, plot_pacf
from scipy.stats import norm
for name in ['results', 'figures']:
    (BASE / name).mkdir(exist_ok=True)
plt.rcParams.update({'font.family':'serif', 'font.size':11, 'axes.spines.top':False,
                     'axes.spines.right':False, 'figure.dpi':140, 'savefig.dpi':180})
BLUE, ORANGE, GREY = '#194c76', '#b34d22', '#707070'
def savefig(name):
    plt.tight_layout()
    image_path = BASE / 'figures' / (name + '.png')
    plt.savefig(image_path, bbox_inches='tight')
    plt.close()
    if 'get_ipython' in globals():
        from IPython.display import display, Image
        display(Image(filename=str(image_path)))
print('Versions:', platform.python_version(), 'numpy', np.__version__, 'pandas', pd.__version__, 'statsmodels', statsmodels.__version__)

# %%
# 1. Audit the unchanged national series. No interpolation or manual correction.
raw_path = BASE / 'data' / 'kazakhstan_generation_snapshot.csv'
raw = pd.read_csv(raw_path, parse_dates=['Date'])
assert raw['Date'].is_unique
assert raw['Generation_TWh'].notna().all()
full = raw.set_index('Date')['Generation_TWh'].sort_index().asfreq('MS')
assert full.notna().all() and (full > 0).all() and len(full) == 102
assert full.index.min() == pd.Timestamp('2018-01-01')
assert full.index.max() == pd.Timestamp('2026-06-01')
repeats = full[full.eq(full.shift())]
audit = {'snapshot_downloaded':'2026-11-18', 'analysis_date':'2026-11-22',
         'source_url':'https://files.ember-energy.org/public-downloads/generation/outputs/release_generation_monthly_global.csv',
         'filter':{'Area':'Kazakhstan','Electricity source':'Total generation','target':'Generation (TWh)'},
         'snapshot_sha256':hashlib.sha256(raw_path.read_bytes()).hexdigest(),
         'n_full':len(full), 'start':str(full.index[0].date()), 'end':str(full.index[-1].date()),
         'missing_targets':int(full.isna().sum()), 'duplicate_dates':0,
         'adjacent_repeats':{str(d.date()):float(v) for d,v in repeats.items()},
         'source_check':{'samruk_january_2018_twh':10.3573,'ember_january_2018_twh':float(full.iloc[0]),
                         'samruk_Q1_2018_twh':29.3392,'ember_Q1_2018_twh':float(full.iloc[:3].sum()),
                         'interpretation':'Quarterly averaging is plausible, not established for all months.'}}
# Chosen on data-quality/calendar grounds before computing model errors.
y = full.loc['2019-01-01':'2025-12-01']
train = y.loc[:'2023-12-01']
validation = y.loc['2024-01-01':'2024-12-01']
test = y.loc['2025-01-01':'2025-12-01']
assert (len(y),len(train),len(validation),len(test)) == (84,60,12,12)
print('Full snapshot:', len(full), 'months; main study:',len(y),'months')
print('Training / validation / test:',len(train),len(validation),len(test))
print('Adjacent exact repeats:',audit['adjacent_repeats'])
print('January 2018 source discrepancy: 9.780 versus 10.3573 TWh')
(BASE/'results'/'data_audit.json').write_text(json.dumps(audit,indent=2))

# %%
# 2. Exploration and stationarity use the INITIAL TRAINING SET only.
fig, ax = plt.subplots(figsize=(9,3.5))
ax.plot(y.index,y.values,color=BLUE,lw=1.5)
ax.axvspan(pd.Timestamp('2024-01-01'),pd.Timestamp('2024-12-31'),color='#e9e9e9',label='Validation: 2024')
ax.axvspan(pd.Timestamp('2025-01-01'),pd.Timestamp('2025-12-31'),color='#f8e7db',label='Test: 2025')
ax.set(ylabel='Monthly generation (TWh)',xlabel='Year')
ax.legend(frameon=False,fontsize=9,loc='upper left',ncol=2)
savefig('01_history')
fig, ax = plt.subplots(figsize=(9,3.4))
for year,g in train.groupby(train.index.year):
    ax.plot(g.index.month,g.values,marker='o',ms=3,lw=1,label=str(year))
ax.set(xticks=range(1,13),xticklabels=['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec'],
       ylabel='Monthly generation (TWh)',xlabel='Month (training data only)')
ax.legend(frameon=False,ncol=5,fontsize=9)
savefig('02_seasonality')
stationarity=[]
for name,z in [('Levels',train),('Seasonal difference',train.diff(12).dropna()),
               ('Seasonal and first difference',train.diff(12).diff().dropna())]:
    adf = adfuller(z,regression='c',autolag='AIC',maxlag=8,result_object=False)
    with warnings.catch_warnings():
        warnings.simplefilter('ignore')
        kp=kpss(z,regression='c',nlags='auto')
    stationarity.append({'Series':name,'n':len(z),'ADF_stat':adf[0],'ADF_p':adf[1],
                         'KPSS_stat':kp[0],'KPSS_p_table_bound':kp[1]})
stationarity=pd.DataFrame(stationarity)
stationarity.to_csv(BASE/'results'/'stationarity.csv',index=False)
fig,axs=plt.subplots(1,2,figsize=(9,3))
plot_acf(train.diff(12).dropna(),lags=20,zero=False,ax=axs[0],title='ACF: seasonal difference')
plot_pacf(train.diff(12).dropna(),lags=20,zero=False,method='ywm',ax=axs[1],title='PACF: seasonal difference')
savefig('03_acf_pacf')
print(stationarity.round(4).to_string(index=False))

# %%
# 3. Eight prespecified low-order candidates. The test year is never used to select.
CANDIDATES = [
    ((1,0,0),(1,1,0,12),'c'), ((1,0,0),(0,1,1,12),'c'),
    ((0,0,1),(0,1,1,12),'c'), ((1,0,1),(0,1,1,12),'c'),
    ((0,1,1),(0,1,1,12),'n'), ((1,1,0),(0,1,1,12),'n'),
    ((0,1,1),(1,1,0,12),'n'), ((1,1,0),(1,1,0,12),'n')]
def label(spec):
    order,season,trend=spec
    return f'SARIMA{order}{season[:3]}[12]' + (' + constant' if trend=='c' else '')
fit_log=[]
def fit_model(hist,spec):
    order,season,trend=spec
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter('always')
        fit=SARIMAX(hist,order=order,seasonal_order=season,trend=trend,
                    enforce_stationarity=True,enforce_invertibility=True).fit(disp=False,maxiter=500)
    ok=bool(fit.mle_retvals.get('converged',False)) and np.isfinite(fit.params).all()
    fit_log.append({'last_training_month':str(hist.index[-1].date()),'model':label(spec),
                    'converged':bool(ok),'warnings':[str(w.message) for w in caught]})
    if not ok:
        raise RuntimeError('Fit did not converge: '+label(spec))
    return fit
def errors(actual,pred):
    e=np.asarray(actual)-np.asarray(pred)
    return {'MAE':float(np.mean(np.abs(e))),'RMSE':float(np.sqrt(np.mean(e**2))),
            'Bias_actual_minus_forecast':float(np.mean(e))}
def backtest(series,start,end,spec=None):
    dates=pd.date_range(start,end,freq='MS'); records=[]
    assert len(dates)%3==0
    for origin in dates[::3]:
        hist=series.loc[series.index<origin]
        assert hist.index.max()<origin
        future=pd.date_range(origin,periods=3,freq='MS')
        if spec is None:
            pred=np.array([hist.loc[d-pd.DateOffset(years=1)] for d in future])
            scale=float(np.sqrt(np.mean(hist.diff(12).dropna()**2)))
            lo80,hi80=pred-norm.ppf(.9)*scale,pred+norm.ppf(.9)*scale
            lo95,hi95=pred-norm.ppf(.975)*scale,pred+norm.ppf(.975)*scale
        else:
            fit=fit_model(hist,spec)
            fc=fit.get_forecast(steps=3)
            pred=np.asarray(fc.predicted_mean)
            ci80=np.asarray(fc.conf_int(alpha=.2)); ci95=np.asarray(fc.conf_int(alpha=.05))
            lo80,hi80=ci80[:,0],ci80[:,1]; lo95,hi95=ci95[:,0],ci95[:,1]
        for i,d in enumerate(future):
            records.append({'Date':d,'origin':hist.index[-1],'horizon':i+1,
                'actual':float(series.loc[d]),'forecast':float(pred[i]),'lower80':float(lo80[i]),
                'upper80':float(hi80[i]),'lower95':float(lo95[i]),'upper95':float(hi95[i])})
    return pd.DataFrame(records)
validation_rows=[]
for i,spec in enumerate(CANDIDATES):
    first_fit=fit_model(train,spec)
    bt=backtest(y,'2024-01-01','2024-12-01',spec)
    validation_rows.append({'candidate':i,'Model':label(spec),'initial_AICc':float(first_fit.aicc),
                            **errors(bt.actual,bt.forecast)})
    print('Validated',label(spec),flush=True)
validation_scores=pd.DataFrame(validation_rows).sort_values(['MAE','initial_AICc'])
selected=CANDIDATES[int(validation_scores.iloc[0]['candidate'])]
validation_scores.to_csv(BASE/'results'/'validation_scores.csv',index=False)
vb=backtest(y,'2024-01-01','2024-12-01')
print('Selected on validation MAE:',label(selected))
print(validation_scores.round(4).to_string(index=False))
print('Validation baseline:',errors(vb.actual,vb.forecast))

# %%
# 4. Frozen model specification, four quarterly forecast origins, same horizons.
baseline=backtest(y,'2025-01-01','2025-12-01')
sarima=backtest(y,'2025-01-01','2025-12-01',selected)
assert baseline.Date.equals(sarima.Date) and baseline.origin.equals(sarima.origin)
all_predictions=pd.concat([baseline.assign(Model='Seasonal naive'),sarima.assign(Model='SARIMA')])
all_predictions.to_csv(BASE/'results'/'test_predictions.csv',index=False)
test_rows=[]
for name,g in all_predictions.groupby('Model',sort=False):
    test_rows.append({'Model':name,**errors(g.actual,g.forecast),
        'Coverage80':float(((g.actual>=g.lower80)&(g.actual<=g.upper80)).mean()),
        'Coverage95':float(((g.actual>=g.lower95)&(g.actual<=g.upper95)).mean())})
test_scores=pd.DataFrame(test_rows)
test_scores.to_csv(BASE/'results'/'test_scores.csv',index=False)
horizon_rows=[]
for (model,h),g in all_predictions.groupby(['Model','horizon']):
    horizon_rows.append({'Model':model,'horizon':h,'n':len(g),**errors(g.actual,g.forecast)})
horizon_scores=pd.DataFrame(horizon_rows)
horizon_scores.to_csv(BASE/'results'/'horizon_scores.csv',index=False)
print(test_scores.round(4).to_string(index=False))
print(horizon_scores.round(4).to_string(index=False))
fig,ax=plt.subplots(figsize=(9,3.8))
ax.fill_between(sarima.Date,sarima.lower95,sarima.upper95,color=BLUE,alpha=.10,label='SARIMA 95% interval')
ax.fill_between(sarima.Date,sarima.lower80,sarima.upper80,color=BLUE,alpha=.15,label='SARIMA 80% interval')
ax.plot(sarima.Date,sarima.actual,color='black',marker='o',label='Actual')
ax.plot(sarima.Date,sarima.forecast,color=BLUE,marker='s',label='SARIMA')
ax.plot(baseline.Date,baseline.forecast,color=ORANGE,ls='--',label='Seasonal naive')
for d in ['2025-04-01','2025-07-01','2025-10-01']:
    ax.axvline(pd.Timestamp(d),color=GREY,alpha=.3,lw=.8)
ax.set(ylabel='Monthly generation (TWh)',xlabel='Test year: 2025 (refit every three months)')
ax.legend(frameon=False,fontsize=8,ncol=2)
savefig('04_test_forecasts')

# %%
# 5. Diagnostics on the pre-test fit, never used to retune after test scoring.
pretest=y.loc[:'2024-12-01']
diagnostic_fit=fit_model(pretest,selected)
burn=max(int(diagnostic_fit.loglikelihood_burn),13)
residuals=diagnostic_fit.resid.iloc[burn:]
model_df=selected[0][0]+selected[0][2]+selected[1][0]+selected[1][2]
ljung=acorr_ljungbox(residuals,lags=[12,24],model_df=model_df,return_df=True)
ljung.to_csv(BASE/'results'/'ljung_box.csv',index_label='lag')
coefficients=pd.DataFrame({'term':diagnostic_fit.param_names,'estimate':diagnostic_fit.params.values,
                           'std_error':diagnostic_fit.bse.values,'p_value':diagnostic_fit.pvalues.values})
coefficients.to_csv(BASE/'results'/'coefficients.csv',index=False)
fig,axs=plt.subplots(2,1,figsize=(9,4.4))
axs[0].plot(residuals.index,residuals.values,color=BLUE,lw=1)
axs[0].axhline(0,color='black',lw=.7)
axs[0].set(ylabel='Residual (TWh)',title='Pre-test fit: observations through December 2024')
plot_acf(residuals,lags=24,zero=False,ax=axs[1],title='Residual autocorrelation')
savefig('05_residuals')
print('Ljung-Box tests (parameter-adjusted):\n',ljung.round(4))
print(coefficients.round(4).to_string(index=False))

# %%
# 6. Sensitivity: same selected specification, add 2018 back without retuning.
sensitivity=backtest(full.loc[:'2025-12-01'],'2025-01-01','2025-12-01',selected)
sensitivity.to_csv(BASE/'results'/'sensitivity_predictions.csv',index=False)
sensitivity_metrics=errors(sensitivity.actual,sensitivity.forecast)
# Illustration beyond the main study endpoint, not a current November forecast.
illustration_fit=fit_model(y,selected)
illustration_fc=illustration_fit.get_forecast(steps=3)
ci=np.asarray(illustration_fc.conf_int(alpha=.05))
illustration=pd.DataFrame({'Date':pd.date_range('2026-01-01',periods=3,freq='MS'),
    'forecast':np.asarray(illustration_fc.predicted_mean),'lower95':ci[:,0],'upper95':ci[:,1]})
illustration.to_csv(BASE/'results'/'dated_forecast_illustration.csv',index=False)
base_mae=float(test_scores.loc[test_scores.Model=='Seasonal naive','MAE'].iloc[0])
model_mae=float(test_scores.loc[test_scores.Model=='SARIMA','MAE'].iloc[0])
summary={'selected_order':list(selected[0]),'selected_seasonal_order':list(selected[1]),'trend':selected[2],
    'selected_label':label(selected),'main_n':len(y),'train_n':len(train),'validation_n':len(validation),
    'test_n':len(test),'baseline_validation':errors(vb.actual,vb.forecast),
    'validation':validation_scores.to_dict('records'),'test':test_scores.to_dict('records'),
    'mae_improvement_percent':100*(base_mae-model_mae)/base_mae,
    'sensitivity_include_2018':sensitivity_metrics,'ljung_box':ljung.reset_index().to_dict('records'),
    'stationarity':stationarity.to_dict('records'),
    'coefficients':coefficients.to_dict('records'),'residual_mean':float(residuals.mean()),
    'residual_sd':float(residuals.std()),'burn_removed':burn,
    'initial_training_seasonal_acf12':float(acf(train,nlags=12)[12]),
    'all_fits_converged':all(r['converged'] for r in fit_log),
    'versions':{'python':platform.python_version(),'numpy':np.__version__,'pandas':pd.__version__,
                'scipy':__import__('scipy').__version__,'statsmodels':statsmodels.__version__,
                'matplotlib':matplotlib.__version__}}
(BASE/'results'/'summary.json').write_text(json.dumps(summary,indent=2))
(BASE/'results'/'fit_log.json').write_text(json.dumps(fit_log,indent=2))
# Chart-ready values also used for editable presentation charts.
chart_data={'history_dates':[d.strftime('%Y-%m') for d in y.index], 'history':y.tolist(),
    'seasonal_months':['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec'],
    'seasonal':{str(k):g.tolist() for k,g in train.groupby(train.index.year)},
    'test_dates':[d.strftime('%b') for d in sarima.Date],
    'actual':sarima.actual.tolist(),'sarima':sarima.forecast.tolist(),'baseline':baseline.forecast.tolist(),
    'lower95':sarima.lower95.tolist(),'upper95':sarima.upper95.tolist(),
    'residual_dates':[d.strftime('%Y-%m') for d in residuals.index], 'residuals':residuals.tolist(),
    'residual_acf':acf(residuals,nlags=24,fft=False).tolist()[1:]}
(BASE/'results'/'chart_data.json').write_text(json.dumps(chart_data,indent=2))
print('MAE reduction versus seasonal naive: %.1f%%' % summary['mae_improvement_percent'])
print('Including 2018, same SARIMA:',sensitivity_metrics)
print('All fits converged:',summary['all_fits_converged'])
print('Dated illustration, information through December 2025:\n',illustration.to_string(index=False,float_format=lambda v:f'{v:.3f}'))
print('No claim of a live forecast for November 2026 is made.')
