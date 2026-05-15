"""Descriptive statistics for the bilateral panel."""
import os

import numpy as np
import pandas as pd
import pyreadstat

ROOT = '/home/user/income-unequal'
OUT = os.path.join(ROOT, 'analysis')

CPTPP = {'AU','BN','CA','CL','JP','MY','MX','NZ','PE','SG','VN'}

df, _ = pyreadstat.read_dta(os.path.join(ROOT, '数据1.dta'))
df['DSTOI2'] = 1.0 - df['DSTRI2']
df['DSTOI1'] = 1.0 - df['DSTRI1']
df['cptpp_post'] = (df['year']>=2018).astype(int) * df['ID2'].isin(CPTPP).astype(int)

var_labels = {
    'lnvalue':         'ln(digital service export value, scaled)',
    'lnvalue_unscale': 'ln(digital service export value, USD)',
    'success':         'Export occurred (0/1)',
    'DSTOI2':          'DSTOI (destination openness = 1-DSTRI2)',
    'DSTRI2':          'DSTRI (destination restrictiveness)',
    'DSTRI1':          'DSTRI (origin)',
    'lngdp1':          'ln(GDP, origin)',
    'lngdp2':          'ln(GDP, destination)',
    'lndis':           'ln(bilateral distance)',
    'Trade':           'Export dependence (X/GDP)',
    'inst':            'Institutional quality',
    'culture':         'Cultural distance',
    'Tariff2':         'Average tariff rate (destination)',
    'RE2':             'R&D expenditure (destination)',
    'Eictsper2':       'Fixed broadband subscriptions (destination)',
    'articles2':       'Scientific articles (destination)',
    'Mobile2':         'Mobile subscriptions (destination)',
    'cptpp_post':      'CPTPP * post-2018 dummy',
}

rows = []
for v, lbl in var_labels.items():
    s = df[v].dropna()
    rows.append({
        'Variable': v, 'Description': lbl,
        'N': len(s), 'Mean': s.mean(), 'SD': s.std(),
        'Min': s.min(), 'P50': s.median(), 'Max': s.max(),
    })

out = pd.DataFrame(rows)
out.to_csv(os.path.join(OUT, 'descriptive_stats.csv'), index=False)
print(out.to_string(index=False,
                    formatters={'Mean':'{:.4f}'.format, 'SD':'{:.4f}'.format,
                                'Min':'{:.4f}'.format, 'P50':'{:.4f}'.format,
                                'Max':'{:.4f}'.format}))

# Year-level digital services exports
print('\n=== Export volume by year ===')
print(df.groupby('year').agg(
    pairs=('lnvalue', 'size'),
    nonzero=('success', 'sum'),
    mean_lnvalue=('lnvalue', 'mean'),
    mean_DSTOI2=('DSTOI2', 'mean'),
).round(4))

# CPTPP vs non-CPTPP destinations openness
print('\n=== Mean openness, CPTPP vs non-CPTPP (destination) ===')
df['dest_is_cptpp'] = df['ID2'].isin(CPTPP).astype(int)
g = df.groupby(['dest_is_cptpp','year'])['DSTOI2'].mean().unstack(0)
g.columns = ['Non-CPTPP', 'CPTPP']
print(g.round(4))
