"""
Eaton-Kortum + Melitz extended digital-trade simulation.

We reproduce the theoretical bridge claimed by the paper:
  τ_{ij}(θ_j) = (1 - θ_j)^{-α} · f_j · (1 - κ · 1{j∈CPTPP})

and the gravity-type export expression that yields

  ∂ ln X_{ij} / ∂ θ_j > 0  with non-linear marginal effect.

We then calibrate the simulation against the empirical DML estimates we
already produced (analysis/dml_extended_results.csv) and compare the
simulated DSTOI->lnexport response to the empirical θ̂_{DML}=2.95** and
the CPTPP→DSTOI mediator θ̂=0.029***.

Outputs:
  analysis/figure1_simulation.png  -- composite Figure 1 for the paper
  analysis/sim_summary.csv         -- scalar summary stats used in prose
"""
import os
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib as mpl

# --- Chinese-friendly font (fallback to default if not available) ---
try:
    # ttc registers under JP subface but contains SC/TC glyphs.
    mpl.rcParams['font.family'] = ['Noto Sans CJK JP', 'Noto Sans CJK SC',
                                    'WenQuanYi Zen Hei', 'sans-serif']
    mpl.rcParams['axes.unicode_minus'] = False
except Exception:
    pass

np.random.seed(20260518)
OUT = os.path.dirname(os.path.abspath(__file__))


# ---------------- model primitives ----------------

def trade_cost(theta, f=1.0, alpha=0.22, kappa=0.18, cptpp=False):
    """Iceberg-type bilateral trade cost as function of openness θ_j.

    τ = (1 - θ)^{α} · f · (1 - κ·1{CPTPP})

    Higher openness θ shrinks (1-θ) so τ decreases (more open ⇒ lower cost).
    α > 0 controls how sharply the cost falls as openness rises (convex);
    κ is the CPTPP-induced reduction in compliance cost (calibrated to the
    ECIPE 18-22% estimate).  Note: the original paper's textual rendering
    "(1-θ)^{-α}" is a typographical sign flip — the intended structural
    relationship is that DSTOI (openness) reduces, not raises, trade cost.
    """
    theta = np.clip(theta, 0.0, 0.999)
    return (1.0 - theta) ** alpha * f * (1.0 - kappa * cptpp)


def exports_gravity(theta, A=1.0, mu=4.0, sigma=3.5, f=1.0,
                    alpha=0.22, kappa=0.18, cptpp=False,
                    n_firms=20000, prod_shape=4.5):
    """Aggregate digital-service exports under Eaton-Kortum + Melitz.

      X_{ij} = A · τ^{-(σ-1)} · Σ_φ [φ^{σ-1} · 1{φ > φ*(τ)}] · g(φ)

    where φ is firm productivity drawn from a Pareto(prod_shape) distribution.
    The cutoff φ* rises with τ (Melitz selection).  We compute Σ via Monte
    Carlo over `n_firms` heterogeneous firms.
    Returns aggregate X (un-logged).
    """
    tau = trade_cost(theta, f=f, alpha=alpha, kappa=kappa, cptpp=cptpp)
    # Pareto productivity draws (truncated to keep numerical stability)
    phi = (np.random.pareto(prod_shape, n_firms) + 1.0)  # >=1
    # Entry cutoff: a firm enters iff revenue covers fixed entry cost f
    # Profit threshold ∝ τ · f^{1/(σ-1)} (simplified Melitz expression).
    phi_star = (tau * f) ** (1.0 / max(sigma - 1, 0.1))
    active = phi > phi_star
    # Sum of φ^{σ-1} over active firms (intensive + extensive margin combined)
    intra = np.sum(phi[active] ** (sigma - 1))
    X = A * (tau ** (-(sigma - 1))) * intra / n_firms * np.exp(mu)
    return X


# ---------------- experiments ----------------

def experiment_openness_curve():
    """Vary θ from 0.30 to 0.95 and trace ln X."""
    thetas = np.linspace(0.30, 0.95, 60)
    lnX = np.array([np.log(exports_gravity(t, n_firms=20000)) for t in thetas])
    # Linear-OLS counterfactual: fit a straight line over the same range
    slope, intercept = np.polyfit(thetas, lnX, 1)
    lnX_linear = intercept + slope * thetas
    return thetas, lnX, lnX_linear, slope


def experiment_cptpp_shift():
    """Compute ΔlnX from CPTPP membership across θ."""
    thetas = np.linspace(0.30, 0.95, 60)
    lnX_nc = np.array([np.log(exports_gravity(t, cptpp=False, n_firms=20000)) for t in thetas])
    lnX_cp = np.array([np.log(exports_gravity(t, cptpp=True,  n_firms=20000)) for t in thetas])
    return thetas, lnX_cp - lnX_nc


def experiment_sector_heterogeneity():
    """Three sectoral productivity profiles (different Pareto shapes).

    - 教育/技术 (k=3.5): heavy tail, high-productivity firms abundant
    - 数字基础设施 (k=4.5): moderate
    - 金融 (k=6.0): light tail, more uniform productivity
    The lower the shape k the more open-ness gains compound (greater
    differential between high-φ firms entering and being squeezed out).
    """
    thetas = np.linspace(0.30, 0.95, 50)
    profiles = {
        '教育—技术': 3.5,
        '数字基础设施': 4.5,
        '金融服务': 6.0,
    }
    out = {}
    for name, k in profiles.items():
        lnX = np.array([np.log(exports_gravity(t, prod_shape=k, n_firms=20000))
                        for t in thetas])
        out[name] = (thetas, lnX)
    return out


def calibrate_against_dml():
    """Return simulation-implied slope and the DML empirical estimate."""
    thetas = np.linspace(0.65, 0.95, 40)  # observed empirical θ range
    lnX = np.array([np.log(exports_gravity(t, n_firms=30000)) for t in thetas])
    slope, _ = np.polyfit(thetas, lnX, 1)
    # Empirical DML estimate (from analysis/dml_extended_results.csv,
    # baseline + 数字化水平 full controls): θ_DML = 2.951, SE = 1.200
    return slope, 2.951, 1.200


# ---------------- plotting ----------------

def plot_figure1():
    fig, axes = plt.subplots(1, 3, figsize=(15, 4.2))

    # Panel A: nonlinear openness-export curve
    ax = axes[0]
    thetas, lnX, lnX_lin, slope = experiment_openness_curve()
    ax.plot(thetas, lnX, 'k--', lw=1.8, label='非线性模拟 (EK+Melitz扩展)')
    ax.plot(thetas, lnX_lin, color='gray', linestyle=':', lw=1.5,
            label='线性基准')
    ax.axvline(0.83, color='red', ls='-', lw=0.7, alpha=0.6)
    ax.text(0.83, lnX.min()+0.3, '样本均值\nθ̄≈0.83', color='red', fontsize=8,
            ha='left', va='bottom')
    ax.set_xlabel('数字服务贸易开放度 θ (DSTOI)')
    ax.set_ylabel('ln(数字服务出口)')
    ax.set_title('(A) 开放度—出口非线性曲线')
    ax.legend(loc='lower right', fontsize=9, frameon=False)
    ax.grid(alpha=0.3)

    # Panel B: CPTPP-induced shift
    ax = axes[1]
    thetas, dln = experiment_cptpp_shift()
    ax.plot(thetas, dln, 'b-', lw=2.0)
    ax.fill_between(thetas, dln, alpha=0.15, color='blue')
    ax.set_xlabel('数字服务贸易开放度 θ')
    ax.set_ylabel('ΔlnX (CPTPP 处置效应)')
    ax.set_title('(B) CPTPP 处置的出口增量')
    # Annotate empirical CPTPP-DSTOI mediator estimate
    ax.text(0.55, dln.max()*0.85,
            '实证: CPTPP→DSTOI\nθ̂=0.029***\n间接传导贡献+0.049',
            fontsize=9, bbox=dict(boxstyle='round', facecolor='wheat',
                                    edgecolor='none', alpha=0.7))
    ax.grid(alpha=0.3)

    # Panel C: sectoral heterogeneity
    ax = axes[2]
    out = experiment_sector_heterogeneity()
    colors = {'教育—技术':'#1f77b4', '数字基础设施':'#2ca02c', '金融服务':'#d62728'}
    for name, (thetas, lnX) in out.items():
        ax.plot(thetas, lnX, lw=1.8, color=colors[name], label=name)
    ax.set_xlabel('数字服务贸易开放度 θ')
    ax.set_ylabel('ln(数字服务出口)')
    ax.set_title('(C) 行业异质性 (Pareto 形状参数差异)')
    ax.legend(loc='lower right', fontsize=9, frameon=False)
    ax.grid(alpha=0.3)

    fig.suptitle('图1  数字服务贸易开放度与出口的理论模拟结果', fontsize=12,
                 fontweight='bold', y=1.02)
    fig.tight_layout()
    path = os.path.join(OUT, 'figure1_simulation.png')
    fig.savefig(path, dpi=180, bbox_inches='tight')
    print(f"Saved figure: {path}")
    return path


def main():
    # Calibrate against DML
    sim_slope, dml_slope, dml_se = calibrate_against_dml()
    print(f"Calibration (over θ ∈ [0.65, 0.95]):")
    print(f"  Simulation slope d(lnX)/dθ = {sim_slope:+.3f}")
    print(f"  Empirical DML θ̂ (full controls)         = {dml_slope:+.3f} (SE={dml_se:.3f})")
    # Save summary
    pd.DataFrame([
        {'metric': 'sim_slope_dlnX_dtheta', 'value': sim_slope},
        {'metric': 'dml_theta_full_controls', 'value': dml_slope},
        {'metric': 'dml_se',                  'value': dml_se},
        {'metric': 'cptpp_to_dstoi',          'value': 0.029},
        {'metric': 'cptpp_indirect_thru_dstoi','value': 0.049},
    ]).to_csv(os.path.join(OUT, 'sim_summary.csv'), index=False)
    plot_figure1()
    print("Done.")


if __name__ == '__main__':
    main()
