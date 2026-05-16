"""
Aggregate data1/2/3/4 to country-year level and merge with data_new.dta.
Map ISO2 (in data1-4) <-> ISO3 (in data_new).
"""
import os
import numpy as np
import pandas as pd
import pyreadstat
import pycountry
import warnings
warnings.filterwarnings('ignore')

ROOT = '/home/user/income-unequal'

# Build ISO2 -> ISO3 mapping
iso2_to_iso3 = {}
for c in pycountry.countries:
    iso2_to_iso3[c.alpha_2] = c.alpha_3

def to_iso3(s):
    return iso2_to_iso3.get(str(s), str(s))


def main():
    # Main panel
    df_main, _ = pyreadstat.read_dta(os.path.join(ROOT, 'data_new.dta'))
    print(f"Main: {df_main.shape}, countries={df_main['country'].nunique()}")

    # --- 数据1: bilateral, take origin (ID1) means per year ---
    df1, _ = pyreadstat.read_dta(os.path.join(ROOT, '数据1.dta'))
    df1_agg = df1.groupby(['ID1','year']).agg(
        productivity_d1=('productivity', 'mean'),
        AI_d1=('AI', 'mean'),
        Tech_d1=('Tech', 'mean'),
        techindex_d1=('techindexA1', 'mean'),
        digit_d1=('digit', 'mean'),
        articles_d1=('articles2', 'mean'),
        re_d1=('RE2', 'mean'),
        culture_d1=('culture', 'mean'),
        inst_d1=('inst', 'mean'),
        secure_d1=('Secure', 'mean'),
        fta_d1=('FTA_1', 'mean'),
    ).reset_index()
    df1_agg['country'] = df1_agg['ID1'].apply(to_iso3)
    df1_agg = df1_agg.drop(columns='ID1')

    # --- 数据2: firm-level M&A, aggregate to country-year ---
    df2, _ = pyreadstat.read_dta(os.path.join(ROOT, '数据2.dta'))
    df2_agg = df2.groupby(['ID1','year']).agg(
        ebit_mean=('EBIT1','mean'),
        assets_mean=('assets1','mean'),
        liabilities_mean=('liabilities1','mean'),
        leverage_mean=('fuzhai1','mean'),
        ma_success_rate=('success','mean'),
        ma_count=('success','size'),
    ).reset_index()
    df2_agg['country'] = df2_agg['ID1'].apply(to_iso3)
    df2_agg = df2_agg.drop(columns='ID1')
    df2_agg['lnma_count'] = np.log1p(df2_agg['ma_count'])

    # --- 数据3: firm-level productivity / AI / Tech ---
    df3, _ = pyreadstat.read_dta(os.path.join(ROOT, '数据3.dta'))
    df3_agg = df3.groupby(['ID1','year']).agg(
        productivity_d3=('productivity','mean'),
        PerData_d3=('PerData','mean'),
        AI_d3=('AI','mean'),
        Tech_d3=('Tech','mean'),
        techindex_d3=('techindexA1','mean'),
        digit_d3=('digit','mean'),
    ).reset_index()
    df3_agg['country'] = df3_agg['ID1'].apply(to_iso3)
    df3_agg = df3_agg.drop(columns='ID1')

    # --- 数据4: WTO LWTariff ---
    df4, _ = pyreadstat.read_dta(os.path.join(ROOT, '数据4.dta'))
    df4 = df4.rename(columns={'ID':'country_iso2'})
    df4['country'] = df4['country_iso2'].apply(to_iso3)
    df4 = df4.drop(columns='country_iso2')

    # Coverage diagnostics
    main_set = set(df_main['country'].unique())
    print(f"Coverage in data1 ISO3: {len(set(df1_agg['country']) & main_set)} / 60")
    print(f"Coverage in data2 ISO3: {len(set(df2_agg['country']) & main_set)} / 60")
    print(f"Coverage in data3 ISO3: {len(set(df3_agg['country']) & main_set)} / 60")
    print(f"Coverage in data4 ISO3: {len(set(df4['country']) & main_set)} / 60")

    # Merge all into main (left join on country, year)
    merged = df_main.copy()
    for src, name in [(df1_agg,'data1'), (df2_agg,'data2'), (df3_agg,'data3'), (df4,'data4')]:
        before = merged.shape[1]
        merged = merged.merge(src, on=['country','year'], how='left')
        new_cols = [c for c in merged.columns[before:]]
        non_null_per_col = merged[new_cols].notna().mean()
        print(f"\nMerged {name}: added {len(new_cols)} cols")
        for c in new_cols:
            print(f"  {c}: {non_null_per_col[c]*100:.1f}% non-null")

    # Save
    out_path = os.path.join(ROOT, 'data_extended.dta')
    # Drop columns starting with '_' (stata estimates store residuals) to make
    # the resulting .dta writable
    keep = [c for c in merged.columns if not c.startswith('_')]
    merged_clean = merged[keep]
    pyreadstat.write_dta(merged_clean, out_path)
    out_csv = os.path.join(ROOT, 'analysis', 'data_extended.csv')
    merged_clean.to_csv(out_csv, index=False)
    print(f"\nSaved: {out_path}  shape={merged_clean.shape}")
    return merged_clean


if __name__ == '__main__':
    main()
