"""
Extended DML analysis addressing the reviewer comments:
1. Enrich mechanism analysis: CPTPP -> {broadband, technology, innovation, M&A activity, productivity}
2. Expand heterogeneity: income, region, by sectoral exposure
   (financial intensity, education/tech intensity, digital infrastructure)
3. Add new controls from data1-4 sources: productivity, AI, Tech, digit, articles,
   institutional quality, security, LWTariff

Uses data_extended.dta (60 countries x 8 years with merged auxiliary variables).
"""
import os
import warnings
import numpy as np
import pandas as pd
import pyreadstat
from sklearn.ensemble import RandomForestRegressor
from sklearn.linear_model import LassoCV
from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import KFold
from scipy import stats

warnings.filterwarnings('ignore')
np.random.seed(20260516)

ROOT = '/home/user/income-unequal'
OUT = os.path.join(ROOT, 'analysis')


# ---------------- DML helpers (same as before) ----------------

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


def rf_pair(seed=42):
    return (RandomForestRegressor(n_estimators=300, min_samples_leaf=3,
                                   max_features=0.7, n_jobs=-1, random_state=seed),
            RandomForestRegressor(n_estimators=300, min_samples_leaf=3,
                                   max_features=0.7, n_jobs=-1, random_state=seed))


def run_dml(df, y, d, controls, learner='rf', n_folds=5, seed=42,
            fe=('id','year'), label=''):
    cols = [y, d] + list(controls)
    sub = df[cols + list(fe)].dropna(subset=cols).reset_index(drop=True)
    if len(sub) < 50:
        return {'theta':np.nan,'se':np.nan,'t':np.nan,'p':np.nan,'n':len(sub),
                'label':label, 'learner':learner, 'y':y, 'd':d}
    fe_arrays = [pd.factorize(sub[c])[0] for c in fe]
    M = sub[cols].values.astype(float)
    Md = iterative_demean(M, fe_arrays, n_iter=10)
    Y = Md[:, 0]; D = Md[:, 1]
    Xc = Md[:, 2:]
    if Xc.shape[1] > 0:
        Xc_s = StandardScaler().fit_transform(Xc)
        ml_l, ml_m = rf_pair(seed=seed)
        res = dml_plr(Y, D, Xc_s, ml_l, ml_m, n_folds=n_folds, seed=seed)
    else:
        if np.sum(D*D) < 1e-12:
            res = {'theta':np.nan,'se':np.nan,'t':np.nan,'p':np.nan,'n':len(Y)}
        else:
            theta = np.sum(Y*D) / np.sum(D*D)
            resid = Y - theta * D; n = len(Y)
            sigma2 = (resid @ resid) / max(n - 1, 1)
            se = np.sqrt(sigma2 / np.sum(D*D))
            t = theta / se if se > 0 else 0
            p = 2 * (1 - stats.norm.cdf(abs(t)))
            res = {'theta':theta,'se':se,'t':t,'p':p,'n':n}
    res.update({'label':label,'learner':learner,'y':y,'d':d})
    return res


def fmt(r):
    if np.isnan(r.get('theta', np.nan)):
        return f"(insufficient data, n={r['n']})"
    star = '***' if r['p']<0.01 else ('**' if r['p']<0.05 else ('*' if r['p']<0.1 else ''))
    return (f"theta={r['theta']:+.4f}{star:3s}  se={r['se']:.4f}  "
            f"t={r['t']:+.2f}  p={r['p']:.4f}  n={r['n']}")


# ---------------- Sector classification ----------------

def classify_sectors(df):
    """Build sectoral exposure tags from data already in the panel.

    Since OECD DSTRI does not publish sector-level scores per country in
    our cleaned data, we proxy sector dominance with country-year
    structural indicators that have direct sectoral interpretation:

    - Finance-intensive: top tertile of |fdi_out_r| (capital-flow intensity)
    - Tech/Education-intensive: top tertile of lnpatent
    - Digital-infra-intensive: top tertile of fixband_r
    - High-AI: AI_d3 above country-year median
    """
    # Country-level mean across years for stable classification
    cmean = df.groupby('country').agg(
        fdi=('fdi_out_r','mean'),
        pat=('lnpatent','mean'),
        infra=('fixband_r','mean'),
        ai=('AI_d3','mean'),
    )
    qfdi = cmean['fdi'].quantile([0.33, 0.67]).values
    qpat = cmean['pat'].quantile([0.33, 0.67]).values
    qinfra = cmean['infra'].quantile([0.33, 0.67]).values

    finance_top = set(cmean[cmean['fdi'] >= qfdi[1]].index)
    tech_top = set(cmean[cmean['pat'] >= qpat[1]].index)
    infra_top = set(cmean[cmean['infra'] >= qinfra[1]].index)

    df = df.copy()
    df['sector_finance'] = df['country'].isin(finance_top).astype(int)
    df['sector_tech_edu'] = df['country'].isin(tech_top).astype(int)
    df['sector_infra'] = df['country'].isin(infra_top).astype(int)
    return df


# ---------------- Main ----------------

CTRL_BASE = ['lngdp','exportd_r','fdi_out_r','fixband_r','lnpatent']
# Extended control set: original + selected new variables from data1/3
CTRL_EXT = CTRL_BASE + ['inst_d1','re_d1','techindex_d1','digit_d1',
                         'articles_d1','PerData_d3']
# Mechanism candidates (outcomes for CPTPP)
MECHANISMS = {
    'fixband_r':     '数字基础设施 (固定宽带)',
    'lnpatent':      '技术创新 (专利)',
    'techindex_d1':  '技术水平指数',
    'AI_d3':         'AI 能力',
    'digit_d1':      '数字化水平',
    're_d1':         '研发支出',
    'ma_success_rate':'跨境并购成功率',
    'productivity_d1':'全要素生产率',
}


def main():
    df, _ = pyreadstat.read_dta(os.path.join(ROOT, 'data_extended.dta'))
    df['cptpp_post'] = df['CCTPP'] * df['post2018']
    df['dstoi_sq'] = df['dstoi'] ** 2
    df = classify_sectors(df)
    print(f"Loaded: N={len(df)} countries={df['country'].nunique()} years={sorted(df['year'].unique())}", flush=True)
    print(f"Sector tags - finance: {df['sector_finance'].sum()} / "
          f"tech-edu: {df['sector_tech_edu'].sum()} / "
          f"infra: {df['sector_infra'].sum()}", flush=True)

    results = []

    # =========== A. Baseline with extended controls ===========
    print('', flush=True)
    print('='*80, flush=True)
    print('A. 基准回归（扩展控制变量）', flush=True)
    print('='*80, flush=True)

    for label, ctrls in [
        ('基准 5 个控制', CTRL_BASE),
        ('+ 制度质量 (inst_d1)', CTRL_BASE + ['inst_d1']),
        ('+ 研发支出 (re_d1)', CTRL_BASE + ['inst_d1','re_d1']),
        ('+ 技术指数 (techindex)', CTRL_BASE + ['inst_d1','re_d1','techindex_d1']),
        ('+ 数字化水平 (digit)', CTRL_BASE + ['inst_d1','re_d1','techindex_d1','digit_d1']),
        ('+ 科研论文 (articles)', CTRL_BASE + ['inst_d1','re_d1','techindex_d1','digit_d1','articles_d1']),
        ('全部扩展 (含 PerData)', CTRL_EXT),
    ]:
        r = run_dml(df, 'lnexport', 'dstoi', ctrls, label=label)
        results.append(r); print(f"  {label:30s}  {fmt(r)}", flush=True)

    # =========== B. Mechanism analysis - CPTPP -> multiple channels ===========
    print('', flush=True)
    print('='*80, flush=True)
    print('B. 机制分析：CPTPP 政策的多渠道传导', flush=True)
    print('='*80, flush=True)
    for mech_var, mech_label in MECHANISMS.items():
        if mech_var not in df.columns:
            continue
        # Remove the outcome variable from controls to avoid perfect prediction
        ctrls = [c for c in CTRL_BASE if c != mech_var]
        r = run_dml(df, mech_var, 'cptpp_post', ctrls,
                    label=f'CPTPP → {mech_label}')
        results.append(r); print(f"  CPTPP → {mech_label:20s}  {fmt(r)}", flush=True)

    # =========== C. Heterogeneity by income group ===========
    print('', flush=True)
    print('='*80, flush=True)
    print('C. 异质性分析 - 收入分组', flush=True)
    print('='*80, flush=True)
    for ig in df['incomegroup'].dropna().unique():
        sub = df[df['incomegroup']==ig]
        if len(sub) < 50: continue
        r = run_dml(sub, 'lnexport', 'dstoi', CTRL_BASE,
                    label=f'income={ig}')
        results.append(r); print(f"  {ig:25s}  {fmt(r)}", flush=True)

    # =========== D. Heterogeneity by region ===========
    print('', flush=True)
    print('='*80, flush=True)
    print('D. 异质性分析 - 地区分组', flush=True)
    print('='*80, flush=True)
    for rg in df['region'].dropna().unique():
        sub = df[df['region']==rg]
        if len(sub) < 50: continue
        r = run_dml(sub, 'lnexport', 'dstoi', CTRL_BASE,
                    label=f'region={rg}')
        results.append(r); print(f"  {rg:25s}  {fmt(r)}", flush=True)

    # =========== E. Sector heterogeneity (NEW - 行业异质性) ===========
    print('', flush=True)
    print('='*80, flush=True)
    print('E. 行业异质性 (金融/教育-技术/基础设施 主导经济体)', flush=True)
    print('='*80, flush=True)
    for sec_var, sec_name in [
        ('sector_finance',  '金融主导经济体'),
        ('sector_tech_edu', '教育-技术主导经济体'),
        ('sector_infra',    '数字基础设施主导经济体'),
    ]:
        sub_hi = df[df[sec_var]==1]
        sub_lo = df[df[sec_var]==0]
        rh = run_dml(sub_hi, 'lnexport', 'dstoi', CTRL_BASE, label=f'{sec_name} (高)')
        rl = run_dml(sub_lo, 'lnexport', 'dstoi', CTRL_BASE, label=f'{sec_name} (低)')
        results.append(rh); results.append(rl)
        print(f"  {sec_name} (高):  {fmt(rh)}", flush=True)
        print(f"  {sec_name} (低):  {fmt(rl)}", flush=True)

    # =========== F. Heterogeneity by openness level (initial DSTOI) ===========
    print('', flush=True)
    print('='*80, flush=True)
    print('F. 异质性分析 - 初始开放度分组（验证非线性）', flush=True)
    print('='*80, flush=True)
    init_dstoi = df[df['year']==2014].groupby('country')['dstoi'].first()
    median_d = init_dstoi.median()
    high_open = set(init_dstoi[init_dstoi >= median_d].index)
    df['initially_high_open'] = df['country'].isin(high_open).astype(int)
    for grp, gname in [(1,'初始高开放度国家'), (0,'初始低开放度国家')]:
        sub = df[df['initially_high_open']==grp]
        r = run_dml(sub, 'lnexport', 'dstoi', CTRL_BASE, label=gname)
        results.append(r); print(f"  {gname:30s}  {fmt(r)}", flush=True)

    # =========== G. Time-period heterogeneity (pre vs post 2018, pre vs post COVID) ===========
    print('', flush=True)
    print('='*80, flush=True)
    print('G. 时期异质性 (CPTPP 生效前后 / COVID 前后)', flush=True)
    print('='*80, flush=True)
    for sub, name in [
        (df[df['year']<=2017], '协定前 2014-2017'),
        (df[df['year']>=2018], '协定后 2018-2021'),
        (df[df['year']<=2019], 'COVID 前 2014-2019'),
        (df[df['year']>=2020], 'COVID 期 2020-2021'),
    ]:
        r = run_dml(sub, 'lnexport', 'dstoi', CTRL_BASE, label=name)
        results.append(r); print(f"  {name:30s}  {fmt(r)}", flush=True)

    # =========== H. Mediation: CPTPP through DSTOI then to exports ===========
    print('', flush=True)
    print('='*80, flush=True)
    print('H. 中介效应分解：CPTPP × DSTOI × 出口', flush=True)
    print('='*80, flush=True)
    r1 = run_dml(df, 'dstoi', 'cptpp_post', CTRL_BASE, label='CPTPP → DSTOI')
    r2 = run_dml(df, 'lnexport', 'dstoi', CTRL_BASE + ['cptpp_post'],
                 label='DSTOI → lnexport | CPTPP')
    r3 = run_dml(df, 'lnexport', 'cptpp_post', CTRL_BASE,
                 label='CPTPP → lnexport (直接 reduced form)')
    results += [r1, r2, r3]
    print(f"  CPTPP → DSTOI:                 {fmt(r1)}", flush=True)
    print(f"  DSTOI → lnexport | CPTPP:      {fmt(r2)}", flush=True)
    print(f"  CPTPP → lnexport (reduced):    {fmt(r3)}", flush=True)
    if not np.isnan(r1['theta']) and not np.isnan(r2['theta']):
        indirect = r1['theta'] * r2['theta']
        print(f"  Indirect (CPTPP→DSTOI→Export): {indirect:+.4f}", flush=True)

    # Save
    out_df = pd.DataFrame([{
        'label':r['label'],'y':r['y'],'d':r['d'],'learner':r.get('learner','rf'),
        'theta':r['theta'],'se':r['se'],'t':r['t'],'p':r['p'],'n':r['n'],
    } for r in results])
    out_df.to_csv(os.path.join(OUT, 'dml_extended_results.csv'), index=False)
    print('', flush=True)
    print(f"Saved {len(results)} results to dml_extended_results.csv", flush=True)


if __name__ == '__main__':
    main()
