"""OLS with two-way FE as a benchmark for DML."""
import os
import numpy as np
import pandas as pd
import pyreadstat
from scipy import stats

ROOT = '/home/user/income-unequal'
OUT = os.path.join(ROOT, 'analysis')
CPTPP = {'AU','BN','CA','CL','JP','MY','MX','NZ','PE','SG','VN'}


def demean(arr, *gs):
    out = arr.astype(float).copy()
    for _ in range(8):
        for g in gs:
            n = int(g.max())+1
            s = np.bincount(g, weights=out, minlength=n)
            c = np.bincount(g, minlength=n)
            out = out - (s/np.maximum(c,1))[g]
    return out


def ols_fe(y, x_cols, df, fe_cols=('year','ID1','ID2')):
    sub = df[[y]+x_cols+list(fe_cols)].dropna().reset_index(drop=True)
    g_arrays = [pd.factorize(sub[c])[0] for c in fe_cols]
    Y = demean(sub[y].values, *g_arrays)
    X = np.column_stack([demean(sub[c].values, *g_arrays) for c in x_cols])
    # add intercept-less OLS
    XtX = X.T @ X
    Xty = X.T @ Y
    beta = np.linalg.solve(XtX, Xty)
    resid = Y - X @ beta
    n, k = X.shape
    sigma2 = (resid @ resid) / (n - k)
    var_beta = sigma2 * np.linalg.inv(XtX)
    se = np.sqrt(np.diag(var_beta))
    t = beta / se
    p = 2 * (1 - stats.norm.cdf(np.abs(t)))
    return pd.DataFrame({
        'var': x_cols, 'coef': beta, 'se': se, 't': t, 'p': p,
    }), n


def main():
    df, _ = pyreadstat.read_dta(os.path.join(ROOT, '数据1.dta'))
    df['DSTOI2'] = 1.0 - df['DSTRI2']
    df['DSTOI2_sq'] = df['DSTOI2'] ** 2
    df['post2018'] = (df['year']>=2018).astype(int)
    df['cptpp_post'] = df['ID2'].isin(CPTPP).astype(int) * df['post2018']

    print('='*78)
    print('OLS with two-way FE (benchmark)')
    print('='*78)

    print('\n(1) lnvalue ~ DSTOI2 + ln-distance  [FE: year+i+j]')
    out, n = ols_fe('lnvalue', ['DSTOI2','lndis'], df)
    print(out.to_string(index=False)); print(f'  N = {n}')

    print('\n(2) lnvalue ~ DSTOI2 + DSTOI2^2 + lndis  [FE: year+i+j]')
    out, n = ols_fe('lnvalue', ['DSTOI2','DSTOI2_sq','lndis'], df)
    print(out.to_string(index=False)); print(f'  N = {n}')

    print('\n(3) lnvalue ~ DSTOI2 + 6 controls  [FE: year+i+j]')
    out, n = ols_fe('lnvalue',
                    ['DSTOI2','lngdp1','lngdp2','lndis','Trade','inst','culture'],
                    df)
    print(out.to_string(index=False)); print(f'  N = {n}')

    print('\n(4) lnvalue ~ cptpp_post  (with lndis as control) [FE: year+i+j]')
    out, n = ols_fe('lnvalue', ['cptpp_post','lndis'], df)
    print(out.to_string(index=False)); print(f'  N = {n}')

    print('\n(5) DSTOI2 ~ cptpp_post  [FE: year+i+j]')
    out, n = ols_fe('DSTOI2', ['cptpp_post','lngdp2','inst'], df)
    print(out.to_string(index=False)); print(f'  N = {n}')

    print('\n(6) Eictsper2 ~ cptpp_post  [FE: year+j]')
    out, n = ols_fe('Eictsper2', ['cptpp_post','lngdp2','Trade'], df,
                    fe_cols=('year','ID2'))
    print(out.to_string(index=False)); print(f'  N = {n}')


if __name__ == '__main__':
    main()
