"""
Fast DML via Frisch-Waugh-Lovell: partial out FE by iterative demeaning,
then cross-fit ML residuals on the within-transformed sample.
"""
import os
import sys
import time
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
os.makedirs(OUT, exist_ok=True)

CPTPP = {'AU','BN','CA','CL','JP','MY','MX','NZ','PE','SG','VN'}

CONTROLS_BASE = [
    'lngdp1','lngdp2','lndis','Trade','inst','culture',
    'Tariff2','RE2','Eictsper2','articles2','Mobile2',
    'gdpfn2','absgdp','techindexA1','techindexA2',
]
CONTROLS_LIGHT = ['lngdp1','lngdp2','lndis','Trade','inst','culture']


def load_data():
    df, _ = pyreadstat.read_dta(os.path.join(ROOT, '数据1.dta'))
    df['DSTOI2'] = 1.0 - df['DSTRI2']
    df['post2018'] = (df['year'] >= 2018).astype(int)
    df['ID2_cptpp'] = df['ID2'].isin(CPTPP).astype(int)
    df['cptpp_post'] = df['ID2_cptpp'] * df['post2018']
    return df


def demean_np(x, groups, n_groups):
    sums = np.bincount(groups, weights=x, minlength=n_groups)
    counts = np.bincount(groups, minlength=n_groups)
    means = sums / np.maximum(counts, 1)
    return x - means[groups]


def iterative_demean(X, fe_arrays, n_iter=8):
    Xd = X.astype(float).copy()
    fe_specs = [(g.astype(np.int64), int(g.max()) + 1) for g in fe_arrays]
    for it in range(n_iter):
        for groups, ng in fe_specs:
            for j in range(Xd.shape[1]):
                Xd[:, j] = demean_np(Xd[:, j], groups, ng)
    return Xd


def dml_plr(Y, D, X, ml_l, ml_m, n_folds=5, seed=42):
    n = len(Y)
    kf = KFold(n_splits=n_folds, shuffle=True, random_state=seed)
    l_hat = np.zeros(n); m_hat = np.zeros(n)
    for tr, te in kf.split(X):
        ml_l.fit(X[tr], Y[tr]); l_hat[te] = ml_l.predict(X[te])
        ml_m.fit(X[tr], D[tr]); m_hat[te] = ml_m.predict(X[te])
    u = Y - l_hat; v = D - m_hat
    theta = np.sum(u*v) / np.sum(v*v)
    psi = (u - v*theta) * v
    J = np.mean(v*v)
    var = np.mean(psi**2) / (J**2) / n
    se = np.sqrt(var)
    t = theta / se if se > 0 else 0
    p = 2 * (1 - stats.norm.cdf(abs(t)))
    return {'theta':theta,'se':se,'t':t,'p':p,'n':n,
            'r2_l':1-np.var(u)/np.var(Y) if np.var(Y)>0 else 0,
            'r2_m':1-np.var(v)/np.var(D) if np.var(D)>0 else 0}


def get_learner(name, seed=42):
    if name == 'rf':
        return (RandomForestRegressor(n_estimators=100, min_samples_leaf=20,
                                       max_features=0.5, n_jobs=-1, random_state=seed),
                RandomForestRegressor(n_estimators=100, min_samples_leaf=20,
                                       max_features=0.5, n_jobs=-1, random_state=seed))
    if name == 'lasso':
        return (LassoCV(cv=5, random_state=seed, max_iter=10000, n_jobs=-1),
                LassoCV(cv=5, random_state=seed, max_iter=10000, n_jobs=-1))
    if name == 'gb':
        return (GradientBoostingRegressor(n_estimators=150, max_depth=3,
                                          learning_rate=0.05, random_state=seed),
                GradientBoostingRegressor(n_estimators=150, max_depth=3,
                                          learning_rate=0.05, random_state=seed))
    if name == 'nnet':
        return (MLPRegressor(hidden_layer_sizes=(64,32), max_iter=300,
                             early_stopping=True, random_state=seed),
                MLPRegressor(hidden_layer_sizes=(64,32), max_iter=300,
                             early_stopping=True, random_state=seed))
    raise ValueError(name)


def run_dml(df, y, d, controls, learner='rf', n_folds=5, seed=42,
            fe_cols=('year','ID1','ID2'), add_sq=False, label=''):
    cols = [y, d] + list(controls)
    sub = df[cols + list(fe_cols)].dropna(subset=cols).reset_index(drop=True)

    fe_arrays = [pd.factorize(sub[c])[0] for c in fe_cols]
    M = sub[cols].values.astype(float)
    Md = iterative_demean(M, fe_arrays, n_iter=6)

    Y = Md[:, 0]; D = Md[:, 1]
    Xc = Md[:, 2:]
    Xc_s = StandardScaler().fit_transform(Xc)
    if add_sq:
        Xc_s = np.hstack([Xc_s, Xc_s ** 2])

    ml_l, ml_m = get_learner(learner, seed=seed)
    res = dml_plr(Y, D, Xc_s, ml_l, ml_m, n_folds=n_folds, seed=seed)
    res.update({'label':label, 'learner':learner, 'n_folds':n_folds,
                'y':y, 'd':d})
    return res


def fmt(r):
    star = '***' if r['p']<0.01 else ('**' if r['p']<0.05 else ('*' if r['p']<0.1 else ''))
    return (f"theta={r['theta']:+.5f}{star:3s}  se={r['se']:.5f}  "
            f"t={r['t']:+.2f}  p={r['p']:.4f}  n={r['n']}")


def main():
    t0 = time.time()
    df = load_data()
    print(f"Loaded: N={len(df)} years={sorted(df['year'].unique())} "
          f"origin={df['ID1'].nunique()} dest={df['ID2'].nunique()}", flush=True)
    print(flush=True)
    results = []

    print('=' * 80, flush=True)
    print('TABLE 2: DSTOI (destination openness = 1 - DSTRI2) -> ln(export value)',
          flush=True)
    print('         FE: year + origin + destination,  K=5 cross-fitted DML-PLR',
          flush=True)
    print('=' * 80, flush=True)

    r = run_dml(df, 'lnvalue','DSTOI2', CONTROLS_LIGHT, learner='rf',
                label='(1) Basic controls')
    results.append(r); print(f"  (1) Basic controls    {fmt(r)}", flush=True)

    r = run_dml(df, 'lnvalue','DSTOI2', CONTROLS_LIGHT, learner='rf',
                add_sq=True, label='(2) +quadratic terms')
    results.append(r); print(f"  (2) +quadratic ctrls  {fmt(r)}", flush=True)

    r = run_dml(df, 'lnvalue','DSTOI2', CONTROLS_BASE, learner='rf',
                label='(3) Full controls')
    results.append(r); print(f"  (3) Full controls     {fmt(r)}", flush=True)

    print(flush=True)
    print('=' * 80, flush=True)
    print('TABLE 3: CPTPP * post-2018 dummy (destination)', flush=True)
    print('=' * 80, flush=True)
    r = run_dml(df, 'lnvalue','cptpp_post', CONTROLS_LIGHT, learner='rf',
                label='CPTPP -> exports (basic)')
    results.append(r); print(f"  CPTPP -> exports, basic   {fmt(r)}", flush=True)
    r = run_dml(df, 'lnvalue','cptpp_post', CONTROLS_BASE, learner='rf',
                label='CPTPP -> exports (full)')
    results.append(r); print(f"  CPTPP -> exports, full    {fmt(r)}", flush=True)
    r = run_dml(df, 'DSTOI2','cptpp_post', CONTROLS_LIGHT, learner='rf',
                label='CPTPP -> DSTOI (basic)')
    results.append(r); print(f"  CPTPP -> DSTOI,   basic   {fmt(r)}", flush=True)
    r = run_dml(df, 'DSTOI2','cptpp_post', CONTROLS_BASE, learner='rf',
                label='CPTPP -> DSTOI (full)')
    results.append(r); print(f"  CPTPP -> DSTOI,   full    {fmt(r)}", flush=True)

    print(flush=True)
    print('=' * 80, flush=True)
    print('TABLE 7: CPTPP -> Fixed broadband (Eictsper2) - mechanism (H3)',
          flush=True)
    print('=' * 80, flush=True)
    r = run_dml(df, 'Eictsper2','cptpp_post', ['lngdp2','Trade','inst'],
                learner='rf', label='CPTPP -> broadband')
    results.append(r); print(f"  CPTPP -> broadband        {fmt(r)}", flush=True)

    print(flush=True)
    print('=' * 80, flush=True)
    print('TABLE 4: Robustness - sample restrictions', flush=True)
    print('=' * 80, flush=True)
    df_nous = df[~df['ID2'].isin({'US','MX'})]
    r = run_dml(df_nous, 'lnvalue','DSTOI2', CONTROLS_BASE, learner='rf',
                label='Drop US/MX (dest)')
    results.append(r); print(f"  (1) Drop US/MX dest       {fmt(r)}", flush=True)

    df_win = df[(df['year']>=2016)&(df['year']<=2020)]
    r = run_dml(df_win, 'lnvalue','DSTOI2', CONTROLS_BASE, learner='rf',
                label='Window 2016-2020')
    results.append(r); print(f"  (2) Window 2016-2020      {fmt(r)}", flush=True)

    df_nc = df[df['ID2_cptpp']==0]
    r = run_dml(df_nc, 'lnvalue','DSTOI2', CONTROLS_BASE, learner='rf',
                label='Non-CPTPP dest only')
    results.append(r); print(f"  (3) Non-CPTPP dest only   {fmt(r)}", flush=True)

    print(flush=True)
    print('=' * 80, flush=True)
    print('TABLE 5: Robustness - alternative ML learners', flush=True)
    print('=' * 80, flush=True)
    for lrn in ['lasso','gb','nnet']:
        r = run_dml(df, 'lnvalue','DSTOI2', CONTROLS_BASE, learner=lrn,
                    label=f'{lrn.upper()}')
        results.append(r); print(f"  {lrn.upper():6s}  {fmt(r)}", flush=True)

    print(flush=True)
    print('Different K folds (cross-fitting):', flush=True)
    for k in [2,3,5,10]:
        r = run_dml(df, 'lnvalue','DSTOI2', CONTROLS_BASE, learner='rf',
                    n_folds=k, label=f'K={k}')
        results.append(r); print(f"  K={k:<2d}    {fmt(r)}", flush=True)

    out_df = pd.DataFrame([{
        'label':r['label'],'y':r['y'],'d':r['d'],'learner':r['learner'],
        'theta':r['theta'],'se':r['se'],'t':r['t'],'p':r['p'],'n':r['n'],
        'r2_l':r['r2_l'],'r2_m':r['r2_m'],
    } for r in results])
    out_df.to_csv(os.path.join(OUT, 'dml_results_fast.csv'), index=False)
    print(flush=True)
    print(f"Total elapsed: {time.time()-t0:.1f}s", flush=True)
    print(f"Saved {len(results)} results to "
          f"{os.path.join(OUT,'dml_results_fast.csv')}", flush=True)


if __name__ == '__main__':
    main()
