"""
Double Machine Learning Analysis: Impact of Digital Service Trade Openness on Digital Service Exports
Replication / re-analysis of Wang & Wang (2026) using the bilateral country-pair panel data.

Note: Data is bilateral (origin x destination x year, 2014-2021). DSTRI2 = destination DSTRI.
DSTOI = 1 - DSTRI2 (destination openness). For exports from i to j, the destination openness matters.
"""
import os
import sys
import warnings

import numpy as np
import pandas as pd
import pyreadstat
from sklearn.ensemble import RandomForestRegressor, GradientBoostingRegressor
from sklearn.linear_model import LassoCV, LogisticRegression
from sklearn.neural_network import MLPRegressor
from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import KFold
from scipy import stats

warnings.filterwarnings('ignore')
np.random.seed(20260515)

ROOT = '/home/user/income-unequal'
OUT = os.path.join(ROOT, 'analysis')
os.makedirs(OUT, exist_ok=True)

CPTPP_MEMBERS = {'AU', 'BN', 'CA', 'CL', 'JP', 'MY', 'MX', 'NZ', 'PE', 'SG', 'VN'}


# ---------------------------- Data ---------------------------- #

def load_data():
    df, _ = pyreadstat.read_dta(os.path.join(ROOT, '数据1.dta'))
    # DSTOI = 1 - DSTRI, destination openness drives exports from i to j
    df['DSTOI2'] = 1.0 - df['DSTRI2']
    df['DSTOI1'] = 1.0 - df['DSTRI1']
    # CPTPP treatment: destination is CPTPP member AND post-2018
    df['post2018'] = (df['year'] >= 2018).astype(int)
    df['ID2_cptpp'] = df['ID2'].isin(CPTPP_MEMBERS).astype(int)
    df['cptpp_post'] = df['ID2_cptpp'] * df['post2018']
    return df


CONTROLS_BASE = [
    'lngdp1', 'lngdp2', 'lndis', 'Trade', 'inst', 'culture',
    'Tariff2', 'RE2', 'Eictsper2', 'articles2', 'Mobile2',
    'gdpfn2', 'absgdp', 'techindexA1', 'techindexA2',
]


def build_sample(df, y='lnvalue', d='DSTOI2', controls=None, drop_na_controls=True):
    if controls is None:
        controls = CONTROLS_BASE
    cols = [y, d] + controls + ['year', 'ID1', 'ID2']
    sub = df[cols].copy()
    if drop_na_controls:
        sub = sub.dropna(subset=[y, d] + controls)
    else:
        # mean-impute missing controls
        for c in controls:
            sub[c] = sub[c].fillna(sub[c].mean())
    return sub.reset_index(drop=True)


def partial_out_fixed_effects(df, target_cols, fe_cols):
    """Within-transform: demean each target column by each FE group sequentially.
    A simple iterative demean for multi-way FE (Gauss-Seidel)."""
    out = df.copy()
    for _ in range(8):
        for fe in fe_cols:
            for c in target_cols:
                out[c] = out[c] - out.groupby(fe)[c].transform('mean')
    return out


# ---------------------------- DML core ---------------------------- #

def dml_plr(Y, D, X, ml_l, ml_m, n_folds=5, seed=42):
    """Partialling-out DML (PLR) following Chernozhukov et al. 2018.
    Y = D*theta + g(X) + e ; D = m(X) + v
    Estimator: theta = E[(Y-l(X))(D-m(X))] / E[(D-m(X))^2]
    where l(X) = E[Y|X].
    Uses K-fold cross-fitting.
    """
    n = len(Y)
    Y = np.asarray(Y).ravel()
    D = np.asarray(D).ravel()
    X = np.asarray(X)

    kf = KFold(n_splits=n_folds, shuffle=True, random_state=seed)
    l_hat = np.zeros(n)
    m_hat = np.zeros(n)

    for tr, te in kf.split(X):
        # E[Y|X]
        ml_l.fit(X[tr], Y[tr])
        l_hat[te] = ml_l.predict(X[te])
        # E[D|X]
        ml_m.fit(X[tr], D[tr])
        m_hat[te] = ml_m.predict(X[te])

    u = Y - l_hat   # residualized outcome
    v = D - m_hat   # residualized treatment

    theta = np.sum(u * v) / np.sum(v * v)
    psi = (u - v * theta) * v
    # Asymptotic variance for orthogonal score
    J = np.mean(v * v)
    var = np.mean(psi ** 2) / (J ** 2) / n
    se = np.sqrt(var)
    t = theta / se
    p = 2 * (1 - stats.norm.cdf(abs(t)))
    return {
        'theta': theta, 'se': se, 't': t, 'p': p,
        'n': n, 'r2_l': 1 - np.var(u) / np.var(Y),
        'r2_m': 1 - np.var(v) / np.var(D),
    }


def get_learner(name, seed=42):
    if name == 'rf':
        return (RandomForestRegressor(n_estimators=200, min_samples_leaf=5,
                                       max_features='sqrt', n_jobs=-1, random_state=seed),
                RandomForestRegressor(n_estimators=200, min_samples_leaf=5,
                                       max_features='sqrt', n_jobs=-1, random_state=seed))
    if name == 'lasso':
        return (LassoCV(cv=5, random_state=seed, max_iter=20000),
                LassoCV(cv=5, random_state=seed, max_iter=20000))
    if name == 'gb':
        return (GradientBoostingRegressor(n_estimators=200, max_depth=3, learning_rate=0.05,
                                          random_state=seed),
                GradientBoostingRegressor(n_estimators=200, max_depth=3, learning_rate=0.05,
                                          random_state=seed))
    if name == 'nnet':
        return (MLPRegressor(hidden_layer_sizes=(64, 32), max_iter=500,
                             early_stopping=True, random_state=seed),
                MLPRegressor(hidden_layer_sizes=(64, 32), max_iter=500,
                             early_stopping=True, random_state=seed))
    raise ValueError(name)


def add_fe_dummies(df_sub, controls):
    """Build the X design: controls + one-hot year + ID1 + ID2 (high-dim)."""
    X = df_sub[controls].copy()
    # standardize numeric columns for ML stability
    scaler = StandardScaler()
    X[controls] = scaler.fit_transform(X[controls])

    # one-hot encode FE (drop_first to avoid singularity, though ML handles it)
    fe_year = pd.get_dummies(df_sub['year'], prefix='yr', drop_first=True).astype(float)
    fe_id1 = pd.get_dummies(df_sub['ID1'], prefix='o', drop_first=True).astype(float)
    fe_id2 = pd.get_dummies(df_sub['ID2'], prefix='d', drop_first=True).astype(float)
    X = pd.concat([X.reset_index(drop=True),
                   fe_year.reset_index(drop=True),
                   fe_id1.reset_index(drop=True),
                   fe_id2.reset_index(drop=True)], axis=1)
    return X.values


def run_one(df, y, d, controls, learner='rf', n_folds=5, seed=42, label=''):
    sub = build_sample(df, y=y, d=d, controls=controls)
    X = add_fe_dummies(sub, controls)
    ml_l, ml_m = get_learner(learner, seed=seed)
    res = dml_plr(sub[y].values, sub[d].values, X, ml_l, ml_m, n_folds=n_folds, seed=seed)
    res['label'] = label
    res['learner'] = learner
    res['n_folds'] = n_folds
    res['y'] = y
    res['d'] = d
    return res


def fmt(r):
    star = '***' if r['p'] < 0.01 else ('**' if r['p'] < 0.05 else ('*' if r['p'] < 0.1 else ''))
    return f"theta={r['theta']:+.4f}{star}  se={r['se']:.4f}  t={r['t']:+.2f}  p={r['p']:.4f}  n={r['n']}"


# ---------------------------- Experiments ---------------------------- #

def main():
    df = load_data()
    print(f"Loaded: N={len(df)}  years={sorted(df['year'].unique())}")
    print(f"Origin countries={df['ID1'].nunique()}  Dest countries={df['ID2'].nunique()}")
    print()

    results = []

    # ============ Table 2: DSTOI on digital service exports ============
    print('=' * 70)
    print('TABLE 2: DSTOI (destination openness) -> ln(export value)')
    print('=' * 70)

    # (1) Baseline: only DSTOI + minimal controls
    r = run_one(df, y='lnvalue', d='DSTOI2',
                controls=['lngdp1', 'lngdp2', 'lndis'],
                learner='rf', label='(1) DSTOI, basic')
    results.append(r); print(f"(1) DSTOI, minimal:  {fmt(r)}")

    # (2) Add quadratic term in controls (capture nonlinearity)
    df['DSTOI2_sq'] = df['DSTOI2'] ** 2
    r = run_one(df, y='lnvalue', d='DSTOI2',
                controls=['lngdp1', 'lngdp2', 'lndis', 'DSTOI2_sq'],
                learner='rf', label='(2) DSTOI, +sq')
    results.append(r); print(f"(2) DSTOI, +DSTOI^2: {fmt(r)}")

    # (3) Full controls
    r = run_one(df, y='lnvalue', d='DSTOI2',
                controls=CONTROLS_BASE,
                learner='rf', label='(3) DSTOI, full controls')
    results.append(r); print(f"(3) DSTOI, full:     {fmt(r)}")

    # ============ Table 3: CPTPP * DSTOI on exports ============
    print()
    print('=' * 70)
    print('TABLE 3: CPTPP membership -> exports / openness')
    print('=' * 70)
    # CPTPP on exports
    r = run_one(df, y='lnvalue', d='cptpp_post',
                controls=['lngdp1', 'lngdp2', 'lndis'],
                learner='rf', label='CPTPP, minimal')
    results.append(r); print(f"(1) CPTPP -> lnvalue, minimal:  {fmt(r)}")

    r = run_one(df, y='lnvalue', d='cptpp_post',
                controls=CONTROLS_BASE,
                learner='rf', label='CPTPP, full')
    results.append(r); print(f"(2) CPTPP -> lnvalue, full:     {fmt(r)}")

    # CPTPP on openness (H2)
    r = run_one(df, y='DSTOI2', d='cptpp_post',
                controls=['lngdp1', 'lngdp2', 'lndis'],
                learner='rf', label='CPTPP -> DSTOI, minimal')
    results.append(r); print(f"(3) CPTPP -> DSTOI,  minimal:   {fmt(r)}")

    r = run_one(df, y='DSTOI2', d='cptpp_post',
                controls=['lngdp1', 'lngdp2', 'lndis', 'Trade', 'inst', 'culture'],
                learner='rf', label='CPTPP -> DSTOI, full')
    results.append(r); print(f"(4) CPTPP -> DSTOI,  full:      {fmt(r)}")

    # Mechanism (H3): CPTPP -> Fixed broadband (Eictsper2)
    r = run_one(df, y='Eictsper2', d='cptpp_post',
                controls=['lngdp1', 'lngdp2', 'lndis'],
                learner='rf', label='CPTPP -> broadband')
    results.append(r); print(f"(5) CPTPP -> broadband:         {fmt(r)}")

    # ============ Table 4: Robustness - sample restrictions ============
    print()
    print('=' * 70)
    print('TABLE 4: Robustness - sample restrictions')
    print('=' * 70)
    # Drop US, MX (per paper)
    df2 = df[~df['ID2'].isin({'US', 'MX'})].copy()
    r = run_one(df2, y='lnvalue', d='DSTOI2',
                controls=CONTROLS_BASE,
                learner='rf', label='Drop US/MX')
    results.append(r); print(f"(1) Drop US/MX dest:            {fmt(r)}")

    # Window 2016-2020 (±2 around 2018)
    df3 = df[(df['year'] >= 2016) & (df['year'] <= 2020)].copy()
    r = run_one(df3, y='lnvalue', d='DSTOI2',
                controls=CONTROLS_BASE,
                learner='rf', label='Window 2016-2020')
    results.append(r); print(f"(2) Window 2016-2020:           {fmt(r)}")

    # Non-CPTPP only (Table 6)
    df4 = df[df['ID2_cptpp'] == 0].copy()
    r = run_one(df4, y='lnvalue', d='DSTOI2',
                controls=CONTROLS_BASE,
                learner='rf', label='Non-CPTPP destinations only')
    results.append(r); print(f"(3) Non-CPTPP dest only:        {fmt(r)}")

    # ============ Table 5: Robustness - different ML algorithms ============
    print()
    print('=' * 70)
    print('TABLE 5: Robustness - different ML learners')
    print('=' * 70)
    for lrn in ['lasso', 'gb', 'nnet']:
        r = run_one(df, y='lnvalue', d='DSTOI2',
                    controls=CONTROLS_BASE,
                    learner=lrn, label=f'DSTOI {lrn}')
        results.append(r); print(f"  {lrn:6s}: {fmt(r)}")

    # Different K (sample-split ratio)
    print()
    print('Different cross-fitting K folds:')
    for k in [2, 3, 5, 8]:
        r = run_one(df, y='lnvalue', d='DSTOI2',
                    controls=CONTROLS_BASE,
                    learner='rf', n_folds=k, label=f'K={k}')
        results.append(r); print(f"  K={k}: {fmt(r)}")

    # Save consolidated results
    out_df = pd.DataFrame([{
        'label': r['label'], 'y': r['y'], 'd': r['d'], 'learner': r['learner'],
        'theta': r['theta'], 'se': r['se'], 't': r['t'], 'p': r['p'], 'n': r['n'],
    } for r in results])
    out_df.to_csv(os.path.join(OUT, 'dml_results.csv'), index=False)
    print()
    print(f"Saved {len(results)} results to {os.path.join(OUT, 'dml_results.csv')}")


if __name__ == '__main__':
    main()
