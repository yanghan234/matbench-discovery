from __future__ import annotations

import matplotlib.pyplot as plt
import pandas as pd
import plotly.graph_objects as go
import pytest

from matbench_discovery.load_preds import load_df_wbm_with_preds
from matbench_discovery.plots import (
    AxLine,
    Backend,
    WhichEnergy,
    cumulative_precision_recall,
    hist_classified_stable_vs_hull_dist,
    rolling_mae_vs_hull_dist,
)

models = ["Wrenformer", "CGCNN", "Voronoi RF"]
df_wbm = load_df_wbm_with_preds(models=models, nrows=100)
e_above_hull_col = "e_above_hull_mp2020_corrected_ppd_mp"
e_form_col = "e_form_per_atom_mp2020_corrected"


@pytest.mark.parametrize(
    "project_end_point,stability_threshold",
    [("", 0), ("x", 0), ("x", -0.05), ("xy", 0.1)],
)
@pytest.mark.parametrize("backend", ("matplotlib", "plotly"))
def test_cumulative_precision_recall(
    project_end_point: AxLine,
    stability_threshold: float,
    backend: Backend,
) -> None:
    fig, df_metrics = cumulative_precision_recall(
        e_above_hull_true=df_wbm[e_above_hull_col],
        df_preds=df_wbm[models],
        backend=backend,
        project_end_point=project_end_point,
        stability_threshold=stability_threshold,
    )

    assert isinstance(df_metrics, pd.DataFrame)
    assert list(df_metrics) == models + ["metric"]

    if backend == "matplotlib":
        assert isinstance(fig, plt.Figure)
        ax1, ax2 = fig.axes
        assert ax1.get_ylim() == ax2.get_ylim() == (0, 1)
        assert ax1.get_ylabel() == "Recall"
        # TODO ax2 ylabel also 'Recall', should be 'Precision'
        # assert ax2.get_ylabel() == "Precision"
    elif backend == "plotly":
        assert isinstance(fig, go.Figure)
        assert fig.layout.yaxis1.title.text == "Precision"
        assert fig.layout.yaxis2.title.text == "Recall"


@pytest.mark.parametrize("window", (0.02, 0.002))
@pytest.mark.parametrize("bin_width", (0.1, 0.001))
@pytest.mark.parametrize("x_lim", ((0, 0.6), (-0.2, 0.8)))
@pytest.mark.parametrize("backend", ("matplotlib", "plotly"))
def test_rolling_mae_vs_hull_dist(
    window: float, bin_width: float, x_lim: tuple[float, float], backend: Backend
) -> None:
    ax = plt.figure().gca()  # new figure ensures test functions use different axes

    for model_name in models:
        ax = rolling_mae_vs_hull_dist(
            e_above_hull_true=df_wbm[model_name],
            e_above_hull_error=df_wbm[e_above_hull_col],
            label=model_name,
            ax=ax,
            x_lim=x_lim,
            window=window,
            bin_width=bin_width,
            backend=backend,
        )

    expected_ylabel = "rolling MAE (eV/atom)"
    if backend == "matplotlib":
        assert isinstance(ax, plt.Axes)
        assert ax.get_ylim() == pytest.approx((0, 0.14))
        assert ax.get_ylabel() == expected_ylabel
        assert ax.get_xlabel() == r"$E_\mathrm{above\ hull}$ (eV/atom)"
    elif backend == "plotly":
        assert isinstance(ax, go.Figure)
        assert ax.layout.yaxis.title.text == expected_ylabel
        assert ax.layout.xaxis.title.text == "E<sub>above hull</sub> (eV/atom)"


@pytest.mark.parametrize("stability_threshold", (0.1, 0.01))
@pytest.mark.parametrize("x_lim", ((0, 0.6), (-0.2, 0.8)))
@pytest.mark.parametrize("which_energy", ("true", "pred"))
@pytest.mark.parametrize("backend", ("plotly", "matplotlib"))
def test_hist_classified_stable_vs_hull_dist(
    stability_threshold: float,
    x_lim: tuple[float, float],
    which_energy: WhichEnergy,
    backend: Backend,
) -> None:
    ax = plt.figure().gca()  # new figure ensures test functions use different axes

    e_above_hull_pred = (
        df_wbm[e_above_hull_col] - df_wbm["Wrenformer"] + df_wbm[e_form_col]
    )
    ax, metrics = hist_classified_stable_vs_hull_dist(
        e_above_hull_pred=e_above_hull_pred,
        e_above_hull_true=df_wbm[e_above_hull_col],
        ax=ax,
        stability_threshold=stability_threshold,
        x_lim=x_lim,
        which_energy=which_energy,
        backend=backend,
    )

    if backend == "matplotlib":
        assert isinstance(ax, plt.Axes)
        assert ax.get_ylabel() == "Number of materials"
    else:
        assert isinstance(ax, go.Figure)
        assert ax.layout.yaxis.title.text == "Number of materials"

    assert metrics["precision"] > 0.3
    assert metrics["recall"] > 0.3
