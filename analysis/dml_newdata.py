"""
DML re-analysis on the clean 60-country × 8-year panel (data_new.dta).
Replicates the paper's Tables 2-7 using DML-PLR with cross-fitting.

Variables (from data_new.dta):
- lnexport        : log digital services export (USD)
- dstoi           : digital service trade openness index (1 - DSTRI), in [0,1]
- CCTPP           : CPTPP membership indicator (constant within country)
- post2018        : 1 if year >= 2018
- cptpp_post      : CCTPP * post2018  (DiD treatment)
- Controls: lngdp, exportd_r (export dependence), fdi_out_r (FDI),
            fixband_r (fixed broadband per capita), lnpatent

Method: Chernozhukov et al. (2018) DML-PLR with within-transformation
        for country + year fixed effects, K-fold cross-fitting,
        and multiple ML learners.
"""
import os
import warnings

import numpy as np
import pandas as pd
import pyreadstat
from sklearn.ensemble import RandomForestRegressor, GradientBoostingRegressor
from sklearn.linear_model import LassoCV
from sklearn.neural_network import MLPRegressor
from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import KFold
from scipy import stats

warnings.filterwarnings('ignore')
np.random.seed(20260515)

ROOT = '/home/user/income-unequal'
OUT = os.path.join(ROOT, 'analysis')

CONTROLS = ['lngdp', 'exportd_r', 'fdi_out_r', 'fixband_r', 'lnpatent']


def load():
    df, _ = pyreadstat.read_dta(os.path.join(ROOT, 'data_new.dta'))
    df['cptpp_post'] = df['CCTPP'] * df['post2018']
    df['dstoi_sq'] = df['dstoi'] ** 2
    df['lngdp_sq'] = df['lngdp'] ** 2
    return df


def demean_np(x, g, ng):
    s = np.bincount(g, weights=x, minlength=ng)
    c = np.bincount(g, minlength=ng)
    return x - (s / np.maximum(c, 1))[g]


def iterative_demean(M, fe_arrays, n_iter=10):
    out = M.astype(float).copy()
    specs = [(g.astype(np.int64), int(g.max())+1) for g in fe_arrays]
    for _ in range(n_iter):
        for g, ng in specs:
            for j in range(out.shape[1]):
                out[:, j] = demean_np(out[:, j], g, ng)
    return out


def dml_plr(Y, D, X, ml_l, ml_m, n_folds=5, seed=42):
    n = len(Y)
    kf = KFold(n_splits=n_folds, shuffle=True, random_state=seed)
    l_hat = np.zeros(n); m_hat = np.zeros(n)
    for tr, te in kf.split(X):
        ml_l.fit(X[tr], Y[tr]); l_hat[te] = ml_l.predict(X[te])
        ml_m.fit(X[tr], D[tr]); m_hat[te] = ml_m.predict(X[te])
    u = Y - l_hat; v = D - m_hat
    if np.sum(v * v) < 1e-12:
        return {'theta':np.nan,'se':np.nan,'t':np.nan,'p':np.nan,'n':n}
    theta = np.sum(u*v) / np.sum(v*v)
    psi = (u - v*theta) * v
    J = np.mean(v*v)
    var = np.mean(psi**2) / (J**2) / n
    se = np.sqrt(var)
    t = theta / se
    p = 2 * (1 - stats.norm.cdf(abs(t)))
    return {'theta':theta,'se':se,'t':t,'p':p,'n':n}


def get_learner(name, seed=42):
    if name == 'rf':
        return (RandomForestRegressor(n_estimators=300, min_samples_leaf=3,
                                       max_features=0.7, n_jobs=-1, random_state=seed),
                RandomForestRegressor(n_estimators=300, min_samples_leaf=3,
                                       max_features=0.7, n_jobs=-1, random_state=seed))
    if name == 'lasso':
        return (LassoCV(cv=5, random_state=seed, max_iter=20000),
                LassoCV(cv=5, random_state=seed, max_iter=20000))
    if name == 'gb':
        return (GradientBoostingRegressor(n_estimators=300, max_depth=3,
                                          learning_rate=0.05, random_state=seed),
                GradientBoostingRegressor(n_estimators=300, max_depth=3,
                                          learning_rate=0.05, random_state=seed))
    if name == 'nnet':
        return (MLPRegressor(hidden_layer_sizes=(32,16), max_iter=2000,
                             early_stopping=True, random_state=seed),
                MLPRegressor(hidden_layer_sizes=(32,16), max_iter=2000,
                             early_stopping=True, random_state=seed))
    raise ValueError(name)


def run_dml(df, y, d, controls, learner='rf', n_folds=5, seed=42,
            fe=('id','year'), label='', extra_features=None):
    cols = [y, d] + list(controls)
    sub = df[cols + list(fe)].dropna(subset=cols).reset_index(drop=True)
    fe_arrays = [pd.factorize(sub[c])[0] for c in fe]
    M = sub[cols].values.astype(float)
    Md = iterative_demean(M, fe_arrays, n_iter=10)
    Y = Md[:, 0]; D = Md[:, 1]
    Xc = Md[:, 2:]
    if Xc.shape[1] > 0:
        Xc_s = StandardScaler().fit_transform(Xc)
        if extra_features is not None:
            Xc_s = np.hstack([Xc_s, extra_features(Md[:, 2:])])
        ml_l, ml_m = get_learner(learner, seed=seed)
        res = dml_plr(Y, D, Xc_s, ml_l, ml_m, n_folds=n_folds, seed=seed)
    else:
        # No controls: simple within-FE OLS on demeaned variables
        if np.sum(D*D) < 1e-12:
            res = {'theta':np.nan,'se':np.nan,'t':np.nan,'p':np.nan,'n':len(Y)}
        else:
            theta = np.sum(Y*D) / np.sum(D*D)
            resid = Y - theta * D
            n = len(Y)
            sigma2 = (resid @ resid) / max(n - 1, 1)
            se = np.sqrt(sigma2 / np.sum(D*D))
            t = theta / se if se > 0 else 0
            p = 2 * (1 - stats.norm.cdf(abs(t)))
            res = {'theta':theta,'se':se,'t':t,'p':p,'n':n}
    res.update({'label':label,'learner':learner,'n_folds':n_folds,
                'y':y,'d':d})
    return res


def fmt(r):
    if np.isnan(r.get('theta', np.nan)):
        return 'singular / no variation after FE'
    star = '***' if r['p']<0.01 else ('**' if r['p']<0.05 else ('*' if r['p']<0.1 else ''))
    return (f"theta={r['theta']:+.4f}{star:3s}  se={r['se']:.4f}  "
            f"t={r['t']:+.2f}  p={r['p']:.4f}  n={r['n']}")


def main():
    df = load()
    print(f"Loaded: N={len(df)}  countries={df['country'].nunique()}  "
          f"years={sorted(df['year'].unique())}", flush=True)
    print(f"Treatment (cptpp_post) rate: {df['cptpp_post'].mean():.4f}", flush=True)
    print(flush=True)
    results = []

    # ====== TABLE 2: DSTOI -> ln(export) ======
    print('=' * 78, flush=True)
    print('TABLE 2: DSTOI -> ln(export)', flush=True)
    print('         FE: country + year,  K=5 cross-fitted DML-PLR (RF)', flush=True)
    print('=' * 78, flush=True)

    # (1) DSTOI only (no controls)
    r = run_dml(df, 'lnexport', 'dstoi', [], learner='rf',
                label='(1) DSTOI only')
    results.append(r); print(f"  (1) DSTOI only        {fmt(r)}", flush=True)

    # (2) DSTOI + DSTOI^2 (paper specification)
    df['_dstoi_only'] = 0.0  # placeholder; we use quadratic as extra feature
    r = run_dml(df, 'lnexport', 'dstoi', ['dstoi_sq'], learner='rf',
                label='(2) DSTOI + DSTOI^2')
    results.append(r); print(f"  (2) DSTOI + DSTOI^2   {fmt(r)}", flush=True)

    # (3) Full controls (paper's main spec)
    r = run_dml(df, 'lnexport', 'dstoi', CONTROLS, learner='rf',
                label='(3) Full controls')
    results.append(r); print(f"  (3) Full controls     {fmt(r)}", flush=True)

    # (4) Full + quadratic
    r = run_dml(df, 'lnexport', 'dstoi', CONTROLS + ['dstoi_sq', 'lngdp_sq'],
                learner='rf', label='(4) Full + quadratics')
    results.append(r); print(f"  (4) Full + quadratics {fmt(r)}", flush=True)

    # ====== TABLE 3: CPTPP * post2018 (DiD treatment) -> lnexport / dstoi ======
    print('', flush=True)
    print('=' * 78, flush=True)
    print('TABLE 3: CPTPP * Post-2018 (DiD treatment)', flush=True)
    print('=' * 78, flush=True)

    r = run_dml(df, 'lnexport', 'cptpp_post', [], learner='rf',
                label='CPTPP -> lnexport, no ctrl')
    results.append(r); print(f"  CPTPP -> lnexport, no ctrl    {fmt(r)}", flush=True)

    r = run_dml(df, 'lnexport', 'cptpp_post', CONTROLS, learner='rf',
                label='CPTPP -> lnexport, full ctrl')
    results.append(r); print(f"  CPTPP -> lnexport, full ctrl  {fmt(r)}", flush=True)

    r = run_dml(df, 'dstoi', 'cptpp_post', [], learner='rf',
                label='CPTPP -> DSTOI, no ctrl')
    results.append(r); print(f"  CPTPP -> DSTOI,    no ctrl    {fmt(r)}", flush=True)

    r = run_dml(df, 'dstoi', 'cptpp_post', CONTROLS, learner='rf',
                label='CPTPP -> DSTOI, full ctrl')
    results.append(r); print(f"  CPTPP -> DSTOI,    full ctrl  {fmt(r)}", flush=True)

    # ====== TABLE 7: H3 mechanism CPTPP -> fixband_r ======
    print('', flush=True)
    print('=' * 78, flush=True)
    print('TABLE 7: H3 mechanism - CPTPP -> fixed broadband (fixband_r)', flush=True)
    print('=' * 78, flush=True)
    r = run_dml(df, 'fixband_r', 'cptpp_post', [], learner='rf',
                label='CPTPP -> broadband, no ctrl')
    results.append(r); print(f"  CPTPP -> broadband, no ctrl   {fmt(r)}", flush=True)

    r = run_dml(df, 'fixband_r', 'cptpp_post',
                ['lngdp','exportd_r','fdi_out_r','lnpatent'],
                learner='rf', label='CPTPP -> broadband, ctrls')
    results.append(r); print(f"  CPTPP -> broadband, ctrls     {fmt(r)}", flush=True)

    # ====== TABLE 4: Robustness - sample restrictions ======
    print('', flush=True)
    print('=' * 78, flush=True)
    print('TABLE 4: Robustness - sample restrictions', flush=True)
    print('=' * 78, flush=True)

    df_nous = df[~df['country'].isin(['USA','MEX'])]
    r = run_dml(df_nous, 'lnexport', 'dstoi', CONTROLS, learner='rf',
                label='Drop USA/MEX')
    results.append(r); print(f"  Drop USA/MEX             {fmt(r)}", flush=True)

    df_win = df[(df['year']>=2016) & (df['year']<=2020)]
    r = run_dml(df_win, 'lnexport', 'dstoi', CONTROLS, learner='rf',
                label='Window 2016-2020')
    results.append(r); print(f"  Window 2016-2020         {fmt(r)}", flush=True)

    df_nc = df[df['CCTPP']==0]
    r = run_dml(df_nc, 'lnexport', 'dstoi', CONTROLS, learner='rf',
                label='Non-CPTPP only')
    results.append(r); print(f"  Non-CPTPP only           {fmt(r)}", flush=True)

    # ====== TABLE 5: Robustness - alternative ML learners ======
    print('', flush=True)
    print('=' * 78, flush=True)
    print('TABLE 5: Robustness - alternative ML learners', flush=True)
    print('=' * 78, flush=True)
    for lrn in ['lasso','gb','nnet']:
        r = run_dml(df, 'lnexport', 'dstoi', CONTROLS, learner=lrn,
                    label=f'DSTOI (full ctrl), {lrn.upper()}')
        results.append(r); print(f"  {lrn.upper():6s} (DSTOI -> lnexport):  {fmt(r)}", flush=True)
    for lrn in ['lasso','gb','nnet']:
        r = run_dml(df, 'lnexport', 'cptpp_post', CONTROLS, learner=lrn,
                    label=f'CPTPP, {lrn.upper()}')
        results.append(r); print(f"  {lrn.upper():6s} (CPTPP -> lnexport):  {fmt(r)}", flush=True)

    print('', flush=True)
    print('K-fold sensitivity (RF, DSTOI):', flush=True)
    for k in [2, 3, 5, 8, 10]:
        r = run_dml(df, 'lnexport', 'dstoi', CONTROLS, learner='rf', n_folds=k,
                    label=f'K={k}')
        results.append(r); print(f"  K={k:<2d}  {fmt(r)}", flush=True)

    # ====== Heterogeneity by region & income group ======
    print('', flush=True)
    print('=' * 78, flush=True)
    print('Heterogeneity: by income group', flush=True)
    print('=' * 78, flush=True)
    for ig in df['incomegroup'].dropna().unique():
        sub = df[df['incomegroup']==ig]
        if len(sub) < 60: continue
        r = run_dml(sub, 'lnexport', 'dstoi', CONTROLS, learner='rf',
                    label=f'income={ig}')
        results.append(r); print(f"  {ig:25s}  {fmt(r)}", flush=True)

    print('', flush=True)
    print('Heterogeneity: by region', flush=True)
    for rg in df['region'].dropna().unique():
        sub = df[df['region']==rg]
        if len(sub) < 60: continue
        r = run_dml(sub, 'lnexport', 'dstoi', CONTROLS, learner='rf',
                    label=f'region={rg}')
        results.append(r); print(f"  {rg:25s}  {fmt(r)}", flush=True)

    out_df = pd.DataFrame([{
        'label':r['label'],'y':r['y'],'d':r['d'],'learner':r['learner'],
        'theta':r['theta'],'se':r['se'],'t':r['t'],'p':r['p'],'n':r['n'],
    } for r in results])
    out_df.to_csv(os.path.join(OUT, 'dml_results_newdata.csv'), index=False)
    print(flush=True)
    print(f"Saved {len(results)} results to {os.path.join(OUT,'dml_results_newdata.csv')}",
          flush=True)


if __name__ == '__main__':
    main()
