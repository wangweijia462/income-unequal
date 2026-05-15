"""OLS with two-way FE benchmark on the clean 60-country panel."""
import os
import numpy as np
import pandas as pd
import pyreadstat
from scipy import stats

ROOT = '/home/user/income-unequal'


def demean(arr, *gs):
    out = arr.astype(float).copy()
    for _ in range(10):
        for g in gs:
            n = int(g.max())+1
            s = np.bincount(g, weights=out, minlength=n)
            c = np.bincount(g, minlength=n)
            out = out - (s/np.maximum(c,1))[g]
    return out


def ols_fe(y, x_cols, df, fe_cols=('id','year'), cluster_col='id'):
    cols_needed = list(dict.fromkeys([y] + x_cols + list(fe_cols) + [cluster_col]))
    sub = df[cols_needed].dropna().reset_index(drop=True)
    g_arrays = [pd.factorize(sub[c])[0] for c in fe_cols]
    Y = demean(sub[y].values, *g_arrays)
    X = np.column_stack([demean(sub[c].values, *g_arrays) for c in x_cols])
    XtX = X.T @ X
    Xty = X.T @ Y
    beta = np.linalg.solve(XtX, Xty)
    resid = Y - X @ beta
    n, k = X.shape
    # cluster-robust SE by country
    cl = pd.factorize(sub[cluster_col])[0]
    G = int(cl.max()) + 1
    bread = np.linalg.inv(XtX)
    meat = np.zeros((k, k))
    for g in range(G):
        mask = (cl == g)
        Xg = X[mask]; rg = resid[mask]
        u = Xg.T @ rg
        meat += np.outer(u, u)
    dfc = (G / (G - 1)) * (n - 1) / (n - k)
    var_beta = dfc * bread @ meat @ bread
    se = np.sqrt(np.diag(var_beta))
    t = beta / se
    p = 2 * (1 - stats.norm.cdf(np.abs(t)))
    return pd.DataFrame({'var': x_cols, 'coef': beta, 'se': se, 't': t, 'p': p}), n


def main():
    df, _ = pyreadstat.read_dta(os.path.join(ROOT, 'data_new.dta'))
    df['cptpp_post'] = df['CCTPP'] * df['post2018']
    df['dstoi_sq'] = df['dstoi'] ** 2

    print('='*72)
    print('OLS with two-way FE (country + year), cluster-robust SE by country')
    print('='*72)

    print('\n(1) lnexport ~ DSTOI')
    out, n = ols_fe('lnexport', ['dstoi'], df)
    print(out.to_string(index=False)); print(f'  N = {n}')

    print('\n(2) lnexport ~ DSTOI + DSTOI^2')
    out, n = ols_fe('lnexport', ['dstoi','dstoi_sq'], df)
    print(out.to_string(index=False)); print(f'  N = {n}')

    print('\n(3) lnexport ~ DSTOI + 5 controls')
    out, n = ols_fe('lnexport',
                    ['dstoi','lngdp','exportd_r','fdi_out_r','fixband_r','lnpatent'], df)
    print(out.to_string(index=False)); print(f'  N = {n}')

    print('\n(4) lnexport ~ cptpp_post (DiD)')
    out, n = ols_fe('lnexport', ['cptpp_post'], df)
    print(out.to_string(index=False)); print(f'  N = {n}')

    print('\n(5) lnexport ~ cptpp_post + controls')
    out, n = ols_fe('lnexport',
                    ['cptpp_post','lngdp','exportd_r','fdi_out_r','fixband_r','lnpatent'], df)
    print(out.to_string(index=False)); print(f'  N = {n}')

    print('\n(6) DSTOI ~ cptpp_post')
    out, n = ols_fe('dstoi', ['cptpp_post'], df)
    print(out.to_string(index=False)); print(f'  N = {n}')

    print('\n(7) DSTOI ~ cptpp_post + lngdp')
    out, n = ols_fe('dstoi', ['cptpp_post','lngdp'], df)
    print(out.to_string(index=False)); print(f'  N = {n}')

    print('\n(8) fixband_r ~ cptpp_post  (H3 mechanism)')
    out, n = ols_fe('fixband_r', ['cptpp_post'], df)
    print(out.to_string(index=False)); print(f'  N = {n}')

    print('\n(9) fixband_r ~ cptpp_post + lngdp + exportd_r')
    out, n = ols_fe('fixband_r', ['cptpp_post','lngdp','exportd_r'], df)
    print(out.to_string(index=False)); print(f'  N = {n}')


if __name__ == '__main__':
    main()
