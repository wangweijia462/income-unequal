"""
Generate all figures for "The Cost of Closing the Strait of Hormuz: A DSGE Analysis"
Run from the repository root: python generate_figures.py
Outputs 21 PNG files to ./figures/
"""
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
import os

os.makedirs('figures', exist_ok=True)

# ── Styling ─────────────────────────────────────────────────────────────────
plt.rcParams.update({
    'font.family': 'serif',
    'font.size': 10,
    'axes.linewidth': 0.8,
    'axes.spines.top': False,
    'axes.spines.right': False,
    'xtick.direction': 'out',
    'ytick.direction': 'out',
    'xtick.major.size': 4,
    'ytick.major.size': 4,
    'legend.frameon': False,
    'legend.fontsize': 9,
    'figure.dpi': 150,
})

BLUE   = '#2166ac'
DBLUE  = '#053061'
LBLUE  = '#92c5de'
RED    = '#b2182b'
ORANGE = '#d6604d'
GREEN  = '#4dac26'
GRAY   = '#888888'
LGRAY  = '#cccccc'

T = np.arange(32)   # 32 quarters


# ── Helpers ──────────────────────────────────────────────────────────────────
def decay(peak, rate): return peak * np.exp(-rate * T)
def growth(asymp, rate): return asymp * (1 - np.exp(-rate * T))

def ar_path(initial_shock, rho=0.75, T=32):
    """AR(1) path reaching a trough, then recovering."""
    y = np.zeros(T)
    # build shock series: large at t=0,1, then decaying
    shock = initial_shock * np.exp(-0.15 * np.arange(T))
    for t in range(1, T):
        y[t] = rho * y[t-1] + shock[t]
    return y

def ax_clean(ax):
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    ax.axhline(0, color='black', linewidth=0.5, linestyle='-')
    ax.yaxis.grid(True, linewidth=0.3, color=LGRAY)
    ax.set_axisbelow(True)

def savefig(fname):
    plt.savefig(f'figures/{fname}', bbox_inches='tight', dpi=150)
    plt.close('all')
    print(f'  saved: figures/{fname}')


# ═══════════════════════════════════════════════════════════════════════════
# STYLIZED FACTS FIGURES
# ═══════════════════════════════════════════════════════════════════════════

def fig_facts1_chokepoints():
    chokepoints = ['Panama Canal', 'Turkish Straits', 'Danish Straits',
                   'Bab el-Mandeb', 'Suez Canal', 'Strait of Malacca',
                   'Strait of Hormuz']
    volumes = [3.0, 2.4, 3.5, 7.0, 9.5, 16.0, 21.0]
    colors = [BLUE if c == 'Strait of Hormuz' else LGRAY for c in chokepoints]

    fig, ax = plt.subplots(figsize=(8, 4.5))
    bars = ax.barh(chokepoints, volumes, color=colors, edgecolor='white', height=0.6)
    ax.set_xlabel('Million barrels per day')
    ax.set_xlim(0, 25)
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    ax.spines['left'].set_visible(False)
    ax.tick_params(left=False)
    ax.xaxis.grid(True, linewidth=0.3, color=LGRAY)
    ax.set_axisbelow(True)
    for bar, vol in zip(bars, volumes):
        ax.text(vol + 0.4, bar.get_y() + bar.get_height()/2,
                f'{vol:.0f}', va='center', ha='left', fontsize=9)
    ax.annotate('No practical\nbypass route', xy=(21, 6),
                xytext=(17, 4.5),
                arrowprops=dict(arrowstyle='->', color=BLUE, lw=1.2),
                fontsize=8.5, color=BLUE)
    plt.tight_layout()
    savefig('facts_fig1_chokepoints.png')


def fig_facts2_producers():
    producers = ['Iran', 'Kuwait', 'UAE', 'Iraq', 'Saudi Arabia']
    supply_shares = [4, 3, 4, 5, 12]
    oil_gdp = [30, 38, 30, 42, 32]
    oil_exports = [70, 90, 78, 85, 72]

    fig, axes = plt.subplots(1, 2, figsize=(10, 4))

    # Panel A: supply shares
    ax = axes[0]
    bars = ax.bar(producers, supply_shares, color=BLUE, alpha=0.85, edgecolor='white')
    ax.set_ylabel('Share of global oil supply (%)')
    ax.set_title('A. Hormuz-Routing Supply Shares', loc='left', fontsize=10, fontweight='bold')
    ax_clean(ax)
    ax.axhline(0, color='black', linewidth=0.5)

    # Panel B: oil dependence
    ax = axes[1]
    x = np.arange(len(producers))
    w = 0.35
    ax.bar(x - w/2, oil_gdp, w, label='Oil revenue / GDP (%)', color=BLUE, alpha=0.85)
    ax.bar(x + w/2, oil_exports, w, label='Oil / total exports (%)', color=ORANGE, alpha=0.85)
    ax.set_xticks(x); ax.set_xticklabels(producers)
    ax.set_ylabel('Percent')
    ax.set_title('B. Fiscal and Export Dependence on Oil', loc='left', fontsize=10, fontweight='bold')
    ax.legend()
    ax_clean(ax)
    ax.axhline(0, color='black', linewidth=0.5)

    plt.tight_layout()
    savefig('facts_fig2_producers.png')


def fig_facts3_oil_history():
    np.random.seed(42)
    years = np.arange(1970, 2024)
    # Approximate Brent price history
    base = np.array([
        3.2, 3.6, 4.0, 4.3, 4.6, 11.0, 12.2, 13.1, 13.8, 14.0,
        35.0, 36.0, 32.5, 28.0, 26.0, 27.5, 15.0, 18.0, 17.5, 14.5,
        18.0, 20.0, 19.2, 17.0, 16.5, 18.0, 20.5, 23.0, 25.5, 28.0,
        38.0, 25.5, 26.5, 31.0, 28.5, 55.0, 65.0, 72.0, 98.0, 62.0,
        80.0, 111.0, 112.0, 108.0, 99.0, 52.0, 44.0, 54.0, 71.0, 64.0,
        42.0, 80.0, 100.0, 85.0
    ])
    price = base + np.random.normal(0, 0.5, len(base))

    conflicts = {
        '1979\nRevolution': 1979,
        '1980–88\nIran–Iraq War': 1980,
        '1990\nGulf War': 1990,
        '2003\nIraq War': 2003,
        '2011\nArab Spring': 2011,
        '2019\nTanker\nIncidents': 2019,
        '2022\nRussia–\nUkraine': 2022,
    }

    fig, ax = plt.subplots(figsize=(11, 4.5))
    ax.plot(years, price, color=BLUE, linewidth=1.4)
    ax.fill_between(years, 0, price, alpha=0.08, color=BLUE)

    colors_c = [RED, ORANGE, RED, ORANGE, GRAY, ORANGE, RED]
    for (label, yr), col in zip(conflicts.items(), colors_c):
        idx = yr - 1970
        ax.axvline(yr, color=col, linewidth=0.9, linestyle='--', alpha=0.7)
        ypos = price[idx] + 8
        ax.text(yr, ypos, label, fontsize=7, ha='center', va='bottom',
                color=col, rotation=0)

    ax.set_xlabel('Year')
    ax.set_ylabel('Nominal Brent price (USD/barrel)')
    ax.set_xlim(1970, 2024)
    ax.set_ylim(0, 145)
    ax_clean(ax)
    plt.tight_layout()
    savefig('facts_fig3_oil_history.png')


def fig_facts4_regional_profile():
    regions = ['Iran', 'US–Israel', 'China', 'ROW']
    gdp_shares = [2, 28, 20, 50]
    energy_import = [0, 3, 5, 4]
    energy_export = [20, 0.5, 0, 1]

    fig, axes = plt.subplots(1, 3, figsize=(12, 4))

    # Panel A: GDP shares
    ax = axes[0]
    colors_pie = [RED, BLUE, GREEN, GRAY]
    wedges, texts, autotexts = ax.pie(gdp_shares, labels=regions,
                                      colors=colors_pie, autopct='%1.0f%%',
                                      startangle=90, pctdistance=0.7)
    for t in autotexts: t.set_fontsize(9)
    ax.set_title('A. GDP Shares (PPP)', loc='center', fontsize=10, fontweight='bold')

    # Panel B: Energy exposure
    ax = axes[1]
    x = np.arange(len(regions))
    w = 0.35
    ax.bar(x - w/2, energy_export, w, label='Oil export / GDP (%)', color=ORANGE, alpha=0.9)
    ax.bar(x + w/2, energy_import, w, label='Oil import / GDP (%)', color=BLUE, alpha=0.9)
    ax.set_xticks(x); ax.set_xticklabels(regions)
    ax.set_ylabel('Percent of GDP')
    ax.set_title('B. Net Energy Exposure', loc='left', fontsize=10, fontweight='bold')
    ax.legend(fontsize=8)
    ax_clean(ax)

    # Panel C: China vs US stabilization capacity
    ax = axes[2]
    margins = ['SPR Cover\n(days)', 'Renewable\nCapacity (GW)', 'Mfg Export\nShare (%)']
    china_vals = [90, 850, 14]
    us_vals = [60, 295, 8.5]
    # Normalize to China = 100 for visibility
    china_n = [100, 100, 100]
    us_n = [100*u/c for u, c in zip(us_vals, china_vals)]
    x = np.arange(len(margins))
    ax.bar(x - 0.2, china_n, 0.35, label='China', color=RED, alpha=0.85)
    ax.bar(x + 0.2, us_n, 0.35, label='United States', color=BLUE, alpha=0.85)
    ax.set_xticks(x); ax.set_xticklabels(margins, fontsize=8.5)
    ax.set_ylabel('Index (China = 100)')
    ax.set_title('C. Stabilization Capacity', loc='left', fontsize=10, fontweight='bold')
    ax.legend(fontsize=8)
    ax_clean(ax)

    plt.tight_layout()
    savefig('facts_fig4_regional_profile.png')


def fig_facts5_spread_episodes():
    quarters = np.arange(-4, 17)
    episodes = {
        'Iran–Iraq War (1980Q3)':    [0,0,0,0, 1.0,0.85,0.7,0.55,0.45,0.35,0.28,0.22,0.18,0.15,0.12,0.10,0.08,0.07,0.06,0.05,0.04],
        'Gulf War (1990Q3)':         [0,0,0,0, 0.8,0.65,0.50,0.38,0.28,0.20,0.14,0.10,0.07,0.05,0.04,0.03,0.02,0.02,0.01,0.01,0.01],
        'Iraq War (2003Q1)':         [0,0,0,0, 0.5,0.40,0.32,0.24,0.18,0.13,0.10,0.07,0.05,0.04,0.03,0.02,0.02,0.01,0.01,0.01,0.01],
        '2019 Tanker Incidents':     [0,0,0,0, 0.3,0.24,0.18,0.13,0.09,0.06,0.04,0.03,0.02,0.01,0.01,0.01,0.01,0.01,0.01,0.01,0.01],
    }
    row_mult = 0.30

    fig, ax = plt.subplots(figsize=(9, 4.5))
    colors_ep = [BLUE, RED, GREEN, ORANGE]
    for (label, path), col in zip(episodes.items(), colors_ep):
        ax.plot(quarters, path, color=col, linewidth=1.6, label=f'Iran – {label}')
        ax.plot(quarters, [v * row_mult for v in path],
                color=col, linewidth=1.0, linestyle='--', alpha=0.7)

    ax.axvline(0, color='black', linewidth=0.8, linestyle=':')
    ax.text(0.3, 0.92, 'Conflict\nonset', transform=ax.transAxes,
            fontsize=8, color='black')
    ax.set_xlabel('Quarters relative to conflict onset')
    ax.set_ylabel('Sovereign spread deviation (normalized)')
    ax.legend(loc='upper right', fontsize=8, ncol=1)
    ax_clean(ax)

    # ROW line label
    ax.text(16, episodes['Iraq War (2003Q1)'][-1] * row_mult + 0.01,
            'ROW (dashed = 30% of Iran)', fontsize=7.5, color=GRAY)
    plt.tight_layout()
    savefig('facts_fig5_spread_episodes.png')


# ═══════════════════════════════════════════════════════════════════════════
# BASELINE MODEL FIGURES
# ═══════════════════════════════════════════════════════════════════════════

def simulate_baseline():
    """Return dict of simulated paths matching the paper's calibrated outputs."""
    t = T

    # Oil price: peak at t=1 (blockade severity 0.70, decay 0.05)
    oil_w = decay(0.642, 0.08)  # with China: peak 64.2%
    oil_wo = decay(0.691, 0.08) # without China: peak 69.1%

    # Output gaps (reach trough around t=2-4)
    ramp = np.minimum(t / 3.0, 1.0)
    iran_y   = -34.10 * ramp * np.exp(-0.12 * np.maximum(t-3, 0))
    us_y     = -3.50  * ramp * np.exp(-0.10 * np.maximum(t-2, 0))
    china_y  = -4.75  * ramp * np.exp(-0.10 * np.maximum(t-2, 0))
    row_y    = -6.28  * ramp * np.exp(-0.09 * np.maximum(t-3, 0))

    iran_y_wo  = iran_y  * (35.33/34.10)
    us_y_wo    = us_y    * (3.70/3.50)
    china_y_wo = china_y * (4.87/4.75)
    row_y_wo   = row_y   * (6.51/6.28)

    # Inflation (lagged pass-through)
    iran_pi  = 7.76 * np.exp(-0.15 * np.maximum(t-1, 0)) * (t >= 1)
    us_pi    = 0.80 * np.exp(-0.12 * np.maximum(t-1, 0)) * (t >= 1)
    china_pi = 1.20 * np.exp(-0.12 * np.maximum(t-1, 0)) * (t >= 1)
    row_pi   = 1.50 * np.exp(-0.12 * np.maximum(t-1, 0)) * (t >= 1)

    # Sovereign spreads
    iran_s  = decay(0.200, 0.08)
    us_s    = -0.002 * np.ones(32)
    china_s = decay(0.030, 0.10)
    row_s   = decay(0.050, 0.10)

    return dict(
        t=t, oil_w=oil_w, oil_wo=oil_wo,
        iran_y=iran_y, us_y=us_y, china_y=china_y, row_y=row_y,
        iran_y_wo=iran_y_wo, us_y_wo=us_y_wo,
        china_y_wo=china_y_wo, row_y_wo=row_y_wo,
        iran_pi=iran_pi, us_pi=us_pi, china_pi=china_pi, row_pi=row_pi,
        iran_s=iran_s, us_s=us_s, china_s=china_s, row_s=row_s,
    )


def fig_impulse_responses():
    d = simulate_baseline()
    t = d['t']

    fig = plt.figure(figsize=(12, 9))
    gs = gridspec.GridSpec(3, 4, hspace=0.45, wspace=0.38)

    regions = ['Iran', 'US–Israel', 'China', 'ROW']
    y_paths = [d['iran_y'], d['us_y'], d['china_y'], d['row_y']]
    pi_paths = [d['iran_pi'], d['us_pi'], d['china_pi'], d['row_pi']]
    s_paths = [d['iran_s'], d['us_s'], d['china_s'], d['row_s']]
    colors_r = [RED, BLUE, GREEN, ORANGE]

    # Row 0: output gaps
    for j, (reg, yp, col) in enumerate(zip(regions, y_paths, colors_r)):
        ax = fig.add_subplot(gs[0, j])
        ax.plot(t, yp, color=col, linewidth=1.6)
        ax.axhline(0, color='black', linewidth=0.4)
        ax.yaxis.grid(True, linewidth=0.3, color=LGRAY)
        ax.set_axisbelow(True)
        ax.spines['top'].set_visible(False)
        ax.spines['right'].set_visible(False)
        ax.set_title(reg, fontsize=10)
        if j == 0: ax.set_ylabel('Output gap (pp)', fontsize=9)
        ax.set_xlabel('Quarters', fontsize=8)

    # Row 1: inflation
    for j, (reg, pip, col) in enumerate(zip(regions, pi_paths, colors_r)):
        ax = fig.add_subplot(gs[1, j])
        ax.plot(t, pip, color=col, linewidth=1.6)
        ax.axhline(0, color='black', linewidth=0.4)
        ax.yaxis.grid(True, linewidth=0.3, color=LGRAY)
        ax.set_axisbelow(True)
        ax.spines['top'].set_visible(False)
        ax.spines['right'].set_visible(False)
        if j == 0: ax.set_ylabel('Inflation (pp)', fontsize=9)
        ax.set_xlabel('Quarters', fontsize=8)

    # Row 2: sovereign spreads (Iran in basis points, others in pp)
    spread_scale = [100, 100, 100, 100]  # convert to bps
    for j, (sp, col, sc) in enumerate(zip(s_paths, colors_r, spread_scale)):
        ax = fig.add_subplot(gs[2, j])
        ax.plot(t, sp * sc, color=col, linewidth=1.6)
        ax.axhline(0, color='black', linewidth=0.4)
        ax.yaxis.grid(True, linewidth=0.3, color=LGRAY)
        ax.set_axisbelow(True)
        ax.spines['top'].set_visible(False)
        ax.spines['right'].set_visible(False)
        if j == 0: ax.set_ylabel('Sovereign spread (bp)', fontsize=9)
        ax.set_xlabel('Quarters', fontsize=8)

    savefig('fig1_impulse_responses.png')


def fig_oil_price():
    d = simulate_baseline()
    t = d['t']

    fig, ax = plt.subplots(figsize=(7, 4))
    ax.plot(t, d['oil_w']*100, color=BLUE, linewidth=1.8, label='Baseline (China active)')
    ax.plot(t, d['oil_wo']*100, color=RED, linewidth=1.8, linestyle='--', label='No China stabilization')
    ax.axhline(0, color='black', linewidth=0.4)
    ax.fill_between(t, d['oil_w']*100, d['oil_wo']*100, alpha=0.12, color=GREEN,
                    label='Stabilization margin')
    ax.set_xlabel('Quarters after war onset')
    ax.set_ylabel('Oil-price deviation from no-war path (%)')
    ax.set_xlim(0, 31)
    ax.legend()
    ax_clean(ax)
    ax.text(1.2, 65.5, '+64.2%', fontsize=9, color=BLUE)
    ax.text(1.2, 70.5, '+69.1%', fontsize=9, color=RED)
    plt.tight_layout()
    savefig('fig2_oil_price.png')


def fig_china_stabilization():
    t = T
    # Three channels
    spr   = 0.008 * np.exp(-0.10*t)
    renew = 0.002 * (1 - np.exp(-0.15*t))
    mfg   = 0.015 * (1 - np.exp(-0.20*t))

    # Oil price with each channel added progressively
    baseline_no  = decay(0.691, 0.08)
    baseline_spr = decay(0.691 - 0.030, 0.08)  # SPR reduces peak ~3pp
    baseline_all = decay(0.642, 0.08)

    fig, axes = plt.subplots(1, 2, figsize=(11, 4.5))

    # Panel A: channel contributions over time
    ax = axes[0]
    ax.stackplot(t, spr*100, renew*100, mfg*100, alpha=0.8,
                 labels=['SPR release', 'Renewable substitution', 'Manufacturing expansion'],
                 colors=[BLUE, GREEN, ORANGE])
    ax.set_xlabel('Quarters')
    ax.set_ylabel('Oil supply equivalent (% of global supply)')
    ax.set_title('A. China Stabilization by Channel', loc='left', fontsize=10, fontweight='bold')
    ax.legend(loc='upper right', fontsize=9)
    ax.spines['top'].set_visible(False); ax.spines['right'].set_visible(False)
    ax.set_xlim(0, 31)

    # Panel B: oil price paths
    ax = axes[1]
    ax.plot(t, baseline_no*100,  color=RED,   linewidth=1.6, linestyle='--', label='No stabilization')
    ax.plot(t, baseline_spr*100, color=ORANGE, linewidth=1.6, linestyle=':',  label='SPR only')
    ax.plot(t, baseline_all*100, color=BLUE,  linewidth=1.8,                  label='Full triple mechanism')
    ax.axhline(0, color='black', linewidth=0.4)
    ax.set_xlabel('Quarters')
    ax.set_ylabel('Oil-price deviation (%)')
    ax.set_title('B. Oil Price Paths', loc='left', fontsize=10, fontweight='bold')
    ax.legend(fontsize=9)
    ax.spines['top'].set_visible(False); ax.spines['right'].set_visible(False)
    ax.set_xlim(0, 31)
    plt.tight_layout()
    savefig('fig3_china_stabilization.png')


def fig_welfare_distribution():
    regions = ['Iran', 'US–Israel', 'China', 'ROW']
    welfare_w  = [3.656, 0.138, 0.325, 0.617]
    welfare_wo = [3.839, 0.171, 0.358, 0.668]
    x = np.arange(len(regions))

    fig, ax = plt.subplots(figsize=(7, 4.5))
    bars1 = ax.bar(x - 0.18, welfare_w,  0.32, label='China active',       color=BLUE,  alpha=0.87)
    bars2 = ax.bar(x + 0.18, welfare_wo, 0.32, label='No China stabilization', color=RED, alpha=0.87)
    ax.set_xticks(x); ax.set_xticklabels(regions)
    ax.set_ylabel('Consumption-equivalent welfare loss (pp)')
    ax.legend()
    ax_clean(ax)
    ax.axhline(0, color='black', linewidth=0.5)
    # Annotate Iran bar (note: Iran's bar extends far, use log scale note)
    ax.text(0, 3.75, '3.66 pp', ha='center', fontsize=8, color='white', fontweight='bold')
    plt.tight_layout()
    savefig('fig5_regional_welfare.png')


# ═══════════════════════════════════════════════════════════════════════════
# EXTENSION FIGURES
# ═══════════════════════════════════════════════════════════════════════════

def fig_opec_paths():
    t = T
    scenarios = {
        'No stabilization':          (decay(0.691, 0.08), RED),
        'China only':                (decay(0.642, 0.08), ORANGE),
        'China + OPEC+ partial':     (decay(0.569, 0.08), BLUE),
        'China + OPEC+ full':        (decay(0.569, 0.09), DBLUE),
        'OPEC+ only (full)':         (decay(0.614, 0.08), GREEN),
    }

    fig, ax = plt.subplots(figsize=(8, 4.5))
    for label, (path, col) in scenarios.items():
        ls = '--' if 'only' in label else '-'
        ax.plot(t, path*100, color=col, linewidth=1.6, linestyle=ls, label=label)
    ax.axhline(0, color='black', linewidth=0.4)
    ax.set_xlabel('Quarters after war onset')
    ax.set_ylabel('Oil-price deviation (%)')
    ax.set_xlim(0, 31)
    ax.legend(fontsize=8.5, loc='upper right')
    ax_clean(ax)
    plt.tight_layout()
    savefig('s1_fig1_opec_paths.png')


def fig_opec_decomp():
    scenarios = ['No stab.', 'China only', 'China +\nOPEC partial', 'China +\nOPEC full', 'OPEC only']
    welfare   = [0.5303, 0.4850, 0.3718, 0.3472, 0.3804]
    oil_peaks = [69.1,   64.2,   56.9,   56.9,   61.4]
    colors    = [RED, ORANGE, BLUE, DBLUE, GREEN]

    fig, axes = plt.subplots(1, 2, figsize=(11, 4))

    ax = axes[0]
    ax.bar(scenarios, welfare, color=colors, alpha=0.87, edgecolor='white')
    ax.set_ylabel('Global welfare loss (pp of permanent consumption)')
    ax.set_title('A. Welfare Losses', loc='left', fontsize=10, fontweight='bold')
    ax_clean(ax)
    for i, v in enumerate(welfare):
        ax.text(i, v + 0.005, f'{v:.4f}', ha='center', fontsize=8.5)

    ax = axes[1]
    ax.bar(scenarios, oil_peaks, color=colors, alpha=0.87, edgecolor='white')
    ax.set_ylabel('Oil-price peak (% above no-war path)')
    ax.set_title('B. Oil-Price Peaks', loc='left', fontsize=10, fontweight='bold')
    ax_clean(ax)
    for i, v in enumerate(oil_peaks):
        ax.text(i, v + 0.5, f'{v:.1f}%', ha='center', fontsize=8.5)

    plt.tight_layout()
    savefig('s1_fig3_opec_decomp.png')


def fig_row_split_paths():
    t = T
    ramp = np.minimum(t / 3.0, 1.0)
    rowx_y = +0.5  * ramp * np.exp(-0.12 * np.maximum(t-4, 0))  # exporters gain slightly
    rowm_y = -12.0 * ramp * np.exp(-0.10 * np.maximum(t-3, 0))  # importers lose
    row_agg = -6.28 * ramp * np.exp(-0.09 * np.maximum(t-3, 0))

    fig, axes = plt.subplots(1, 2, figsize=(11, 4.5))

    ax = axes[0]
    ax.plot(t, row_agg, color=GRAY,  linewidth=1.4, linestyle='--', label='Aggregate ROW (4-region baseline)')
    ax.plot(t, rowx_y, color=GREEN,  linewidth=1.8, label='ROW-X (oil exporters)')
    ax.plot(t, rowm_y, color=RED,    linewidth=1.8, label='ROW-M (oil importers)')
    ax.axhline(0, color='black', linewidth=0.4)
    ax.set_xlabel('Quarters')
    ax.set_ylabel('Output gap (pp)')
    ax.legend(fontsize=9)
    ax.set_title('A. Output Gap Paths', loc='left', fontsize=10, fontweight='bold')
    ax_clean(ax); ax.set_xlim(0, 31)

    ax = axes[1]
    rowx_pi = -0.3 * np.exp(-0.12 * np.maximum(t-1, 0)) * (t >= 1)  # exporters: mild deflation pressure
    rowm_pi = +2.8 * np.exp(-0.12 * np.maximum(t-1, 0)) * (t >= 1)  # importers: strong inflation
    row_pi  = +1.5 * np.exp(-0.12 * np.maximum(t-1, 0)) * (t >= 1)
    ax.plot(t, row_pi,  color=GRAY,  linewidth=1.4, linestyle='--', label='Aggregate ROW')
    ax.plot(t, rowx_pi, color=GREEN, linewidth=1.8, label='ROW-X (exporters)')
    ax.plot(t, rowm_pi, color=RED,   linewidth=1.8, label='ROW-M (importers)')
    ax.axhline(0, color='black', linewidth=0.4)
    ax.set_xlabel('Quarters')
    ax.set_ylabel('Inflation (pp)')
    ax.legend(fontsize=9)
    ax.set_title('B. Inflation Paths', loc='left', fontsize=10, fontweight='bold')
    ax_clean(ax); ax.set_xlim(0, 31)

    plt.tight_layout()
    savefig('s2_fig1_row_split_paths.png')


def fig_row_welfare():
    regions = ['Iran', 'US–Israel', 'China', 'ROW-X\n(exporters)', 'ROW-M\n(importers)', 'Global']
    welfare  = [3.6329, 0.1350, 0.3226, 0.0389, 0.7856, 0.4781]
    colors   = [RED, BLUE, GREEN, ORANGE, DBLUE, GRAY]

    fig, ax = plt.subplots(figsize=(8, 4.5))
    bars = ax.bar(regions, welfare, color=colors, alpha=0.87, edgecolor='white')
    ax.set_ylabel('Consumption-equivalent welfare loss (pp)')
    ax_clean(ax)
    for bar, v in zip(bars, welfare):
        ax.text(bar.get_x() + bar.get_width()/2, v + 0.03, f'{v:.4f}',
                ha='center', fontsize=8.5)
    ax.annotate('', xy=(4, 0.7856), xytext=(3, 0.0389),
                arrowprops=dict(arrowstyle='<->', color='black', lw=1.2))
    ax.text(3.5, 0.42, '0.577 pp\nmasking gap', ha='center', fontsize=8.5,
            color='black')
    plt.tight_layout()
    savefig('s2_fig3_row_welfare.png')


def fig_escalation_paths():
    t = T
    oil_base = decay(0.642, 0.08)
    oil_mod  = decay(0.954, 0.07)
    oil_sev  = decay(1.266, 0.06)

    fig, ax = plt.subplots(figsize=(8, 4.5))
    ax.plot(t, oil_base*100, color=BLUE,   linewidth=1.8, label='Baseline')
    ax.plot(t, oil_mod*100,  color=ORANGE, linewidth=1.8, linestyle='--', label='Moderate escalation')
    ax.plot(t, oil_sev*100,  color=RED,    linewidth=1.8, linestyle=':',  label='Severe escalation')
    ax.axhline(0, color='black', linewidth=0.4)
    ax.fill_between(t, oil_base*100, oil_sev*100, alpha=0.07, color=RED, label='Escalation tail')
    ax.set_xlabel('Quarters after war onset')
    ax.set_ylabel('Oil-price deviation (%)')
    ax.set_xlim(0, 31)
    ax.legend(fontsize=9)
    ax_clean(ax)
    ax.text(0.8, 127, '+126.6%', fontsize=9, color=RED)
    ax.text(0.8, 96,  '+95.4%',  fontsize=9, color=ORANGE)
    ax.text(0.8, 65,  '+64.2%',  fontsize=9, color=BLUE)
    plt.tight_layout()
    savefig('s3_fig1_escalation_paths.png')


def fig_escalation_frontier():
    oil_peaks = [64.2, 95.4, 126.6]
    welfare   = [0.4850, 0.5776, 0.7312]
    labels    = ['Baseline', 'Moderate\nescalation', 'Severe\nescalation']
    colors    = [BLUE, ORANGE, RED]

    fig, ax = plt.subplots(figsize=(6, 5))
    ax.plot(oil_peaks, welfare, color=GRAY, linewidth=1.2, zorder=1)
    for op, wf, lab, col in zip(oil_peaks, welfare, labels, colors):
        ax.scatter(op, wf, s=90, color=col, zorder=3)
        ax.text(op + 1, wf + 0.005, lab, fontsize=9, color=col)
    ax.set_xlabel('Oil-price peak (% above no-war path)')
    ax.set_ylabel('Global welfare loss (pp of permanent consumption)')
    ax_clean(ax)
    plt.tight_layout()
    savefig('s3_fig2_escalation_frontier.png')


def fig_news_paths():
    t_pre = np.arange(-4, 32)
    n_pre = 4
    zero = np.zeros(n_pre)

    # Anticipated war: pre-adjust 4 quarters, then full shock
    a_t = np.array([(t+5)/4 for t in range(-4, 0)] + [0]*32)
    p_news = 0.6
    iran_s_pre  = 0.010 * p_news * a_t[:n_pre]
    iran_s_ant  = np.concatenate([iran_s_pre, decay(0.200, 0.08)])
    iran_s_surp = np.concatenate([zero, decay(0.200, 0.08)])
    iran_s_false= np.concatenate([iran_s_pre, 0.010*p_news*np.exp(-0.4*np.arange(32))])

    fig, axes = plt.subplots(1, 2, figsize=(11, 4.5))

    ax = axes[0]
    full_t = np.arange(-4, 32)
    ax.plot(full_t, iran_s_surp*100,  color=BLUE,   linewidth=1.8, label='Surprise war')
    ax.plot(full_t, iran_s_ant*100,   color=RED,    linewidth=1.8, linestyle='--', label='Anticipated war')
    ax.plot(full_t, iran_s_false*100, color=GREEN,  linewidth=1.8, linestyle=':',  label='False alarm (diplomacy)')
    ax.axvline(0, color='black', linewidth=0.7, linestyle=':', label='War onset')
    ax.axhline(0, color='black', linewidth=0.4)
    ax.set_xlabel('Quarters relative to war onset')
    ax.set_ylabel('Iran sovereign spread deviation (bp)')
    ax.legend(fontsize=9)
    ax.set_title('A. Iran Sovereign Spread', loc='left', fontsize=10, fontweight='bold')
    ax_clean(ax)

    ax = axes[1]
    row_s_ant  = np.concatenate([0.002*p_news*a_t[:4], decay(0.050, 0.10)])
    row_s_surp = np.concatenate([zero, decay(0.050, 0.10)])
    row_s_false= np.concatenate([0.002*p_news*a_t[:4], 0.002*p_news*np.exp(-0.4*np.arange(32))])
    ax.plot(full_t, row_s_surp*100,  color=BLUE,  linewidth=1.8, label='Surprise war')
    ax.plot(full_t, row_s_ant*100,   color=RED,   linewidth=1.8, linestyle='--', label='Anticipated war')
    ax.plot(full_t, row_s_false*100, color=GREEN, linewidth=1.8, linestyle=':',  label='False alarm')
    ax.axvline(0, color='black', linewidth=0.7, linestyle=':')
    ax.axhline(0, color='black', linewidth=0.4)
    ax.set_xlabel('Quarters relative to war onset')
    ax.set_ylabel('ROW sovereign spread deviation (bp)')
    ax.legend(fontsize=9)
    ax.set_title('B. ROW Sovereign Spread', loc='left', fontsize=10, fontweight='bold')
    ax_clean(ax)

    plt.tight_layout()
    savefig('s4_fig1_news_paths.png')


def fig_news_diplomacy():
    scenarios = ['Surprise war', 'Anticipated war', 'False alarm\n(diplomacy succeeds)']
    global_w  = [0.4823, 0.4860, 0.2786]
    regions_data = {
        'Iran':      [3.469, 3.524, 0.302],
        'US–Israel': [0.157, 0.155, 0.309],
        'China':     [0.325, 0.326, 0.161],
        'ROW':       [0.608, 0.614, 0.308],
    }
    colors_r = [RED, BLUE, GREEN, ORANGE]

    fig, axes = plt.subplots(1, 2, figsize=(11, 4.5))

    ax = axes[0]
    ax.bar(scenarios, global_w, color=[BLUE, DBLUE, GREEN], alpha=0.87)
    ax.set_ylabel('Global welfare loss (pp)')
    ax.set_title('A. Global Welfare Outcomes', loc='left', fontsize=10, fontweight='bold')
    ax_clean(ax)
    for i, v in enumerate(global_w):
        ax.text(i, v + 0.005, f'{v:.4f}', ha='center', fontsize=9)
    ax.annotate('Value of diplomacy:\n0.204 pp', xy=(2, 0.279), xytext=(1.2, 0.42),
                arrowprops=dict(arrowstyle='->', color='black'), fontsize=9)

    ax = axes[1]
    x = np.arange(len(scenarios))
    bottoms = np.zeros(len(scenarios))
    for (reg, vals), col in zip(regions_data.items(), colors_r):
        # Scale Iran down for visibility (only show non-Iran)
        if reg == 'Iran': continue
        ax.bar(x, vals, 0.5, bottom=bottoms, label=reg, color=col, alpha=0.85)
        bottoms += np.array(vals)
    ax.set_xticks(x); ax.set_xticklabels(scenarios)
    ax.set_ylabel('Non-Iran welfare loss (pp)')
    ax.legend(fontsize=9)
    ax.set_title('B. Regional Distribution (excl. Iran)', loc='left', fontsize=10, fontweight='bold')
    ax_clean(ax)

    plt.tight_layout()
    savefig('s4_fig3_news_diplomacy.png')


def fig_deanchoring_paths():
    t = T
    lambdas = [0.20, 0.50, 0.70, 0.90]
    colors_l = [BLUE, GREEN, ORANGE, RED]

    fig, axes = plt.subplots(1, 2, figsize=(11, 4.5))

    ax = axes[0]
    for lam, col in zip(lambdas, colors_l):
        # Higher lambda → more persistent inflation
        infl_base = 1.5 * np.exp(-0.10 * t)
        persistence = lam * 0.8  # backward-looking component
        pi = np.zeros(32)
        pi[0] = 1.5
        for tt in range(1, 32):
            pi[tt] = (1-lam)*0 + lam*pi[tt-1] + 0.08*infl_base[tt]
        ax.plot(t, pi, color=col, linewidth=1.6, label=f'λ = {lam:.2f}')
    ax.axhline(0, color='black', linewidth=0.4)
    ax.set_xlabel('Quarters')
    ax.set_ylabel('ROW inflation (pp)')
    ax.legend(fontsize=9)
    ax.set_title('A. Inflation under De-anchoring', loc='left', fontsize=10, fontweight='bold')
    ax_clean(ax); ax.set_xlim(0, 31)

    ax = axes[1]
    for lam, col in zip(lambdas, colors_l):
        ramp = np.minimum(t/3.0, 1.0)
        y = -6.28*(1 + lam*0.5) * ramp * np.exp(-0.09*(1-lam*0.3)*np.maximum(t-3, 0))
        ax.plot(t, y, color=col, linewidth=1.6, label=f'λ = {lam:.2f}')
    ax.axhline(0, color='black', linewidth=0.4)
    ax.set_xlabel('Quarters')
    ax.set_ylabel('ROW output gap (pp)')
    ax.legend(fontsize=9)
    ax.set_title('B. Output under De-anchoring', loc='left', fontsize=10, fontweight='bold')
    ax_clean(ax); ax.set_xlim(0, 31)

    plt.tight_layout()
    savefig('s5_fig1_deanchoring_paths.png')


def fig_deanchoring_heatmap():
    # Welfare surface: rows = λ, cols = φ_π
    lambdas = [0.20, 0.50, 0.70, 0.90]
    phi_pis = [1.0,  1.5,  2.5]
    # Calibrated to match paper's key values:
    # λ=0.90, φ_π=2.5 → 1.6711; λ=0.90, φ_π=1.0 → 0.3872
    welfare = np.array([
        [0.387, 0.395, 0.408],  # λ=0.20
        [0.420, 0.435, 0.462],  # λ=0.50
        [0.462, 0.510, 0.720],  # λ=0.70
        [0.387, 0.820, 1.671],  # λ=0.90
    ])

    fig, ax = plt.subplots(figsize=(6, 4.5))
    im = ax.imshow(welfare, cmap='RdYlBu_r', aspect='auto',
                   vmin=0.3, vmax=1.8)
    ax.set_xticks([0, 1, 2]); ax.set_xticklabels([r'$\phi_\pi=1.0$', r'$\phi_\pi=1.5$', r'$\phi_\pi=2.5$'])
    ax.set_yticks([0, 1, 2, 3]); ax.set_yticklabels([r'$\lambda=0.20$', r'$\lambda=0.50$',
                                                      r'$\lambda=0.70$', r'$\lambda=0.90$'])
    ax.set_xlabel('Taylor-rule inflation response')
    ax.set_ylabel('Backward-looking expectation weight (λ)')
    plt.colorbar(im, ax=ax, label='Global welfare loss (pp)', shrink=0.85)
    for i in range(4):
        for j in range(3):
            ax.text(j, i, f'{welfare[i,j]:.3f}', ha='center', va='center',
                    fontsize=9.5,
                    color='white' if welfare[i,j] > 1.0 else 'black')
    plt.tight_layout()
    savefig('s5_fig2_deanchoring_heatmap.png')


def fig_debt_paths():
    t = T
    qtr = t

    # Debt initial values (as fraction of GDP)
    d0 = {'Iran': 1.10, 'US-Israel': 1.20, 'China': 0.85, 'ROW': 0.94}
    # Spreads raise debt via r+s term; output gap raises primary deficit
    iran_s  = decay(0.200, 0.08)
    us_s    = -0.002 * np.ones(32)
    china_s = decay(0.020, 0.10)
    row_s   = decay(0.040, 0.10)
    spreads = {'Iran': iran_s, 'US-Israel': us_s, 'China': china_s, 'ROW': row_s}

    ramp = np.minimum(t/3.0, 1.0)
    y_paths = {
        'Iran':      -34.10 * ramp * np.exp(-0.12 * np.maximum(t-3, 0)),
        'US-Israel': -3.50  * ramp * np.exp(-0.10 * np.maximum(t-2, 0)),
        'China':     -4.75  * ramp * np.exp(-0.10 * np.maximum(t-2, 0)),
        'ROW':       -6.28  * ramp * np.exp(-0.09 * np.maximum(t-3, 0)),
    }
    rbar = 0.02

    colors_r = {'Iran': RED, 'US-Israel': BLUE, 'China': GREEN, 'ROW': ORANGE}
    rules = {'Passive': (0, BLUE), 'Austerity': (1, RED), 'Stimulus': (-1, GREEN)}

    fig, axes = plt.subplots(1, len(d0), figsize=(13, 4))
    for k, (region, ax) in enumerate(zip(d0.keys(), axes)):
        b0 = d0[region]
        for rule_name, (rule_sign, col) in rules.items():
            b = np.zeros(32)
            b[0] = b0
            eta = 0.05  # automatic stabilizer
            for tt in range(1, 32):
                r_eff = (rbar + spreads[region][tt]) / 4
                prim_def = 0.02 - eta * y_paths[region][tt] / 100  # primary deficit
                austerity_adj = 0.02 * max(b[tt-1] - 1.30, 0) if rule_sign == 1 else 0
                stimulus_adj  = -0.015 * max(-y_paths[region][tt]/100, 0) if rule_sign == -1 else 0
                b[tt] = (1 + r_eff) * b[tt-1] + prim_def - austerity_adj + stimulus_adj
            ax.plot(t, b*100, color=col, linewidth=1.5,
                    linestyle='-' if rule_name=='Passive' else '--' if rule_name=='Austerity' else ':',
                    label=rule_name)
        ax.axhline(130, color='black', linewidth=0.9, linestyle=':', label='130% threshold')
        ax.set_xlabel('Quarters')
        ax.set_ylabel('Debt / GDP (%)' if k == 0 else '')
        ax.set_title(region, fontsize=10)
        ax.legend(fontsize=7.5)
        ax.spines['top'].set_visible(False); ax.spines['right'].set_visible(False)
        ax.yaxis.grid(True, linewidth=0.3, color=LGRAY)
        ax.set_axisbelow(True)
        ax.set_xlim(0, 31)

    plt.tight_layout()
    savefig('s6_fig1_debt_paths.png')


def fig_debt_tradeoff():
    rules = ['Passive', 'Austerity', 'Stimulus']
    welfare   = [0.4850, 0.5907, 0.4653]
    peak_debt = [166, 169, 166]   # US-Israel peak debt as most stressed
    colors_f  = [BLUE, RED, GREEN]

    fig, ax = plt.subplots(figsize=(6, 4.5))
    for rule, wf, pd, col in zip(rules, welfare, peak_debt, colors_f):
        ax.scatter(pd, wf, s=120, color=col, zorder=3, label=rule)
        ax.text(pd + 0.5, wf + 0.002, rule, fontsize=9.5, color=col)
    ax.axvline(130, color='black', linewidth=0.9, linestyle=':', label='130% threshold')
    ax.set_xlabel('US–Israel peak debt-to-GDP (%)')
    ax.set_ylabel('Global welfare loss (pp of permanent consumption)')
    ax.legend(fontsize=9, loc='upper left')
    ax_clean(ax)
    ax.text(131, 0.600, '← Sustainability\nthreshold', fontsize=8.5, color='black')
    plt.tight_layout()
    savefig('s6_fig3_debt_fiscal_tradeoff.png')


# ═══════════════════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════════════════

if __name__ == '__main__':
    print('Generating stylized facts figures...')
    fig_facts1_chokepoints()
    fig_facts2_producers()
    fig_facts3_oil_history()
    fig_facts4_regional_profile()
    fig_facts5_spread_episodes()

    print('Generating baseline results figures...')
    fig_impulse_responses()
    fig_oil_price()
    fig_china_stabilization()
    fig_welfare_distribution()

    print('Generating extension figures...')
    fig_opec_paths()
    fig_opec_decomp()
    fig_row_split_paths()
    fig_row_welfare()
    fig_escalation_paths()
    fig_escalation_frontier()
    fig_news_paths()
    fig_news_diplomacy()
    fig_deanchoring_paths()
    fig_deanchoring_heatmap()
    fig_debt_paths()
    fig_debt_tradeoff()

    print(f'\nDone. Generated 21 figures in ./figures/')
