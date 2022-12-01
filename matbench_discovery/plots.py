from __future__ import annotations

from typing import Any, Literal

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import plotly.express as px
import plotly.io as pio
import scipy.interpolate
import scipy.stats
import wandb
from mpl_toolkits.axes_grid1.anchored_artists import AnchoredSizeBar

from matbench_discovery.energy import classify_stable

__author__ = "Janosh Riebesell"
__date__ = "2022-08-05"

WhichEnergy = Literal["true", "pred"]
AxLine = Literal["x", "y", "xy", ""]


# --- start global plot settings
quantity_labels = dict(
    n_atoms="Atom Count",
    n_elems="Element Count",
    crystal_sys="Crystal system",
    spg_num="Space group",
    n_wyckoff="Number of Wyckoff positions",
    n_sites="Lattice site count",
    energy_per_atom="Energy (eV/atom)",
    e_form="Formation energy (eV/atom)",
    e_above_hull="Energy above convex hull (eV/atom)",
    e_above_hull_pred="Predicted energy above convex hull (eV/atom)",
    e_above_hull_mp="Energy above MP convex hull (eV/atom)",
    e_above_hull_error="Error in energy above convex hull (eV/atom)",
    vol_diff="Volume difference (A^3)",
    e_form_per_atom_mp2020_corrected="Formation energy (eV/atom)",
    e_form_per_atom_pred="Predicted formation energy (eV/atom)",
    material_id="Material ID",
    band_gap="Band gap (eV)",
    formula="Formula",
)
model_labels = dict(
    wren="Wren",
    wrenformer="Wrenformer",
    m3gnet="M3GNet",
    bowsr_megnet="BOWSR + MEGNet",
    cgcnn="CGCNN",
    voronoi="Voronoi",
    wbm="WBM",
    dft="DFT",
)
px.defaults.labels = quantity_labels | model_labels

pio.templates.default = "plotly_white"

# https://github.com/plotly/Kaleido/issues/122#issuecomment-994906924
# when seeing MathJax "loading" message in exported PDFs, try:
# pio.kaleido.scope.mathjax = None


plt.rc("font", size=14)
plt.rc("legend", fontsize=16, title_fontsize=16)
plt.rc("axes", titlesize=16, labelsize=16)
plt.rc("savefig", bbox="tight", dpi=200)
plt.rc("figure", dpi=200, titlesize=16)
plt.rcParams["figure.constrained_layout.use"] = True
# --- end global plot settings


def hist_classified_stable_vs_hull_dist(
    e_above_hull_true: pd.Series,
    e_above_hull_pred: pd.Series,
    ax: plt.Axes = None,
    which_energy: WhichEnergy = "true",
    stability_threshold: float = 0,
    show_threshold: bool = True,
    x_lim: tuple[float | None, float | None] = (-0.4, 0.4),
    rolling_accuracy: float | None = 0.02,
) -> tuple[plt.Axes, dict[str, float]]:
    """
    Histogram of the energy difference (either according to DFT ground truth [default]
    or model predicted energy) to the convex hull for materials in the WBM data set. The
    histogram is broken down into true positives, false negatives, false positives, and
    true negatives based on whether the model predicts candidates to be below the known
    convex hull. Ideally, in discovery setting a model should exhibit high recall, i.e.
    the majority of materials below the convex hull being correctly identified by the
    model.

    See fig. S1 in https://science.org/doi/10.1126/sciadv.abn4117.

    Args:
        e_above_hull_true (pd.Series): Distance to convex hull according to DFT
            ground truth (in eV / atom).
        e_above_hull_pred (pd.Series): Distance to convex hull predicted by model
            (in eV / atom). Same as true energy to convex hull plus predicted minus true
            formation energy.
        ax (plt.Axes, optional): matplotlib axes to plot on.
        which_energy (WhichEnergy, optional): Whether to use the true (DFT) hull
            distance or the model's predicted hull distance for the histogram.
        stability_threshold (float, optional): set stability threshold as distance to
            convex hull in eV/atom, usually 0 or 0.1 eV.
        show_threshold (bool, optional): Whether to plot stability threshold as dashed
            vertical line.
        x_lim (tuple[float | None, float | None]): x-axis limits.
        rolling_accuracy (float): Rolling accuracy window size in eV / atom. Set to None
            or 0 to disable. Defaults to 0.01.

    Returns:
        tuple[plt.Axes, dict[str, float]]: plot axes and classification metrics

    NOTE this figure plots hist bars separately which causes aliasing in pdf. Can be
    fixed in Inkscape or similar by merging regions by color.
    """
    ax = ax or plt.gca()

    true_pos, false_neg, false_pos, true_neg = classify_stable(
        e_above_hull_true, e_above_hull_pred, stability_threshold
    )
    n_true_pos = sum(true_pos)
    n_false_neg = sum(false_neg)

    n_total_pos = n_true_pos + n_false_neg
    null = n_total_pos / len(e_above_hull_true)

    # toggle between histogram of DFT-computed/model-predicted distance to convex hull
    e_above_hull = e_above_hull_true if which_energy == "true" else e_above_hull_pred
    eah_true_pos = e_above_hull[true_pos]
    eah_false_neg = e_above_hull[false_neg]
    eah_false_pos = e_above_hull[false_pos]
    eah_true_neg = e_above_hull[true_neg]
    xlabel = dict(
        true="$E_\\mathrm{above\\ hull}$ (eV / atom)",
        pred="$E_\\mathrm{above\\ hull\\ pred}$ (eV / atom)",
    )[which_energy]

    ax.hist(
        [eah_true_pos, eah_false_neg, eah_false_pos, eah_true_neg],
        bins=200,
        range=x_lim,
        alpha=0.5,
        color=["tab:green", "tab:orange", "tab:red", "tab:blue"],
        label=[
            "True Positives",
            "False Negatives",
            "False Positives",
            "True Negatives",
        ],
        stacked=True,
    )

    n_true_pos, n_false_pos, n_true_neg, n_false_neg = map(
        len, (eah_true_pos, eah_false_pos, eah_true_neg, eah_false_neg)
    )
    # null = (tp + fn) / (tp + tn + fp + fn)
    precision = n_true_pos / (n_true_pos + n_false_pos)

    # assert (n_all := n_true_pos + n_false_pos + n_true_neg + n_false_neg) == len(
    #     e_above_hull_true
    # ), f"{n_all} != {len(e_above_hull_true)}"

    ax.set(xlabel=xlabel, ylabel="Number of compounds", xlim=x_lim)

    if rolling_accuracy:
        # add moving average of the accuracy (computed within 20 meV/atom intervals) as
        # a function of ΔHd,MP is shown as a blue line (right axis)
        ax_acc = ax.twinx()
        ax_acc.set_ylabel("Accuracy", color="darkblue")
        ax_acc.tick_params(labelcolor="darkblue")
        ax_acc.set(ylim=(0, 1))

        # --- moving average of the accuracy
        # compute accuracy within 20 meV/atom intervals
        bins = np.arange(x_lim[0], x_lim[1], rolling_accuracy)
        bin_counts = np.histogram(e_above_hull_true, bins)[0]
        bin_true_pos = np.histogram(eah_true_pos, bins)[0]
        bin_true_neg = np.histogram(eah_true_neg, bins)[0]

        # compute accuracy
        bin_accuracies = (bin_true_pos + bin_true_neg) / bin_counts
        # plot accuracy
        ax_acc.plot(
            bins[:-1],
            bin_accuracies,
            color="tab:blue",
            label="Accuracy",
            linewidth=3,
        )
        # ax2.fill_between(
        #     bin_centers,
        #     bin_accuracy - bin_accuracy_std,
        #     bin_accuracy + bin_accuracy_std,
        #     color="tab:blue",
        #     alpha=0.2,
        # )

    if show_threshold:
        ax.axvline(
            stability_threshold,
            color="k",
            linestyle="--",
            label="Stability Threshold",
        )

    recall = n_true_pos / n_total_pos

    return ax, {
        "enrichment": precision / null,
        "precision": precision,
        "recall": recall,
        "prevalence": null,
        "accuracy": (n_true_pos + n_true_neg)
        / (n_true_pos + n_true_neg + n_false_pos + n_false_neg),
        "f1": 2 * (precision * recall) / (precision + recall),
    }


def rolling_mae_vs_hull_dist(
    e_above_hull_true: pd.Series,
    e_above_hull_pred: pd.Series,
    half_window: float = 0.02,
    bin_width: float = 0.002,
    x_lim: tuple[float, float] = (-0.2, 0.3),
    ax: plt.Axes = None,
    **kwargs: Any,
) -> plt.Axes:
    """Rolling mean absolute error as the energy to the convex hull is varied. A scale
    bar is shown for the windowing period of 40 meV per atom used when calculating
    the rolling MAE. The standard error in the mean is shaded
    around each curve. The highlighted V-shaped region shows the area in which the
    average absolute error is greater than the energy to the known convex hull. This is
    where models are most at risk of misclassifying structures.
    """
    ax = ax or plt.gca()

    is_fresh_ax = len(ax.lines) == 0

    bins = np.arange(*x_lim, bin_width)

    rolling_maes = np.zeros_like(bins)
    rolling_stds = np.zeros_like(bins)
    for idx, bin_center in enumerate(bins):
        low = bin_center - half_window
        high = bin_center + half_window

        mask = (e_above_hull_true <= high) & (e_above_hull_true > low)
        rolling_maes[idx] = e_above_hull_pred.loc[mask].abs().mean()
        rolling_stds[idx] = scipy.stats.sem(e_above_hull_pred.loc[mask].abs())

    kwargs = dict(linewidth=3) | kwargs
    ax.plot(bins, rolling_maes, **kwargs)

    ax.fill_between(
        bins, rolling_maes + rolling_stds, rolling_maes - rolling_stds, alpha=0.3
    )

    if not is_fresh_ax:
        # return earlier if all plot objects besides the line were already drawn by a
        # previous call
        return ax

    scale_bar = AnchoredSizeBar(
        ax.transData,
        2 * half_window,
        "40 meV",
        "lower left",
        pad=0.5,
        frameon=False,
        size_vertical=0.002,
    )
    # indicate size of MAE averaging window
    ax.add_artist(scale_bar)

    # DFT accuracy at 25 meV/atom for relative e_above_hull which is lower than
    # formation energy error due to systematic error cancellation among
    # similar chemistries, supporting ref:
    # https://journals.aps.org/prb/abstract/10.1103/PhysRevB.85.155208
    dft_acc = 0.025
    ax.plot((dft_acc, 1), (dft_acc, 1), color="grey", linestyle="--", alpha=0.3)
    ax.plot((-1, -dft_acc), (1, dft_acc), color="grey", linestyle="--", alpha=0.3)
    ax.plot(
        (-dft_acc, dft_acc), (dft_acc, dft_acc), color="grey", linestyle="--", alpha=0.3
    )
    ax.fill_between(
        (-1, -dft_acc, dft_acc, 1),
        (1, 1, 1, 1),
        (1, dft_acc, dft_acc, 1),
        color="tab:red",
        alpha=0.2,
    )

    ax.plot((0, dft_acc), (0, dft_acc), color="grey", linestyle="--", alpha=0.3)
    ax.plot((-dft_acc, 0), (dft_acc, 0), color="grey", linestyle="--", alpha=0.3)
    ax.fill_between(
        (-dft_acc, 0, dft_acc),
        (dft_acc, dft_acc, dft_acc),
        (dft_acc, 0, dft_acc),
        color="tab:orange",
        alpha=0.2,
    )
    # shrink=0.1 means cut off 10% length from both sides of arrow line
    arrowprops = dict(
        facecolor="black", width=0.5, headwidth=5, headlength=5, shrink=0.1
    )
    ax.annotate(
        xy=(-dft_acc, dft_acc),
        xytext=(-2 * dft_acc, dft_acc),
        text="Corrected\nGGA DFT\nAccuracy",
        arrowprops=arrowprops,
        verticalalignment="center",
        horizontalalignment="right",
    )

    ax.text(0, 0.13, r"$|E_\mathrm{above\ hull}| > $MAE", horizontalalignment="center")
    ax.set(xlabel=r"$E_\mathrm{above\ hull}$ (eV / atom)", ylabel="MAE (eV / atom)")
    ax.set(xlim=x_lim, ylim=(0.0, 0.14))

    return ax


def cumulative_clf_metric(
    e_above_hull_true: pd.Series,
    e_above_hull_pred: pd.Series,
    metric: Literal["precision", "recall"],
    stability_threshold: float = 0,  # set stability threshold as distance to convex
    # hull in eV / atom, usually 0 or 0.1 eV
    ax: plt.Axes = None,
    label: str = None,
    project_end_point: AxLine = "xy",
    show_optimal: bool = False,
    **kwargs: Any,
) -> plt.Axes:
    """Precision and recall as a function of the number of included materials sorted
    by model-predicted distance to the convex hull, i.e. materials predicted most stable
    enter the precision and recall calculation first. The curves end when all materials
    predicted stable are included.

    Args:
        e_above_hull_true (pd.Series): Distance to convex hull according to DFT
            ground truth (in eV / atom).
        e_above_hull_pred (pd.Series): Distance to convex hull predicted by model
            (in eV / atom). Same as true energy to convex hull plus predicted minus true
            formation energy.
        metric ('precision' | 'recall', optional): Metric to plot.
        stability_threshold (float, optional): Max distance from convex hull before
            material is considered unstable. Defaults to 0.
        label (str, optional): Model name used to identify its liens in the legend.
            Defaults to None.
        project_end_point ('x' | 'y' | 'xy' | '', optional): Defaults to '', i.e. no
            axis projection lines.
        show_optimal (bool, optional): Whether to plot the optimal precision/recall
            line. Defaults to False.
        **kwargs: Keyword arguments passed to ax.plot().

    Returns:
        plt.Axes: The matplotlib axes object.
    """
    ax = ax or plt.gca()

    e_above_hull_pred = e_above_hull_pred.sort_values()
    e_above_hull_true = e_above_hull_true.loc[e_above_hull_pred.index]

    true_pos, false_neg, false_pos, _true_neg = classify_stable(
        e_above_hull_true, e_above_hull_pred, stability_threshold
    )

    true_pos_cumsum = true_pos.cumsum()

    # precision aka positive predictive value (PPV)
    precision = true_pos_cumsum / (true_pos_cumsum + false_pos.cumsum()) * 100
    n_true_pos = sum(true_pos)
    n_false_neg = sum(false_neg)
    n_total_pos = n_true_pos + n_false_neg
    true_pos_rate = true_pos_cumsum / n_total_pos * 100

    end = int(np.argmax(true_pos_rate))
    xs = np.arange(end)

    ys_raw = dict(precision=precision, recall=true_pos_rate)[metric]
    y_interp = scipy.interpolate.interp1d(xs, ys_raw[:end], kind="cubic")
    ys = y_interp(xs)

    line_kwargs = dict(
        linewidth=2, markevery=[-1], marker="x", markersize=14, markeredgewidth=2.5
    )
    ax.plot(xs, ys, **line_kwargs | kwargs)
    ax.text(
        xs[-1],
        ys[-1],
        label,
        color=kwargs.get("color"),
        verticalalignment="bottom",
        rotation=30,
        bbox=dict(facecolor="white", alpha=0.5, edgecolor="none"),
    )

    # add some visual guidelines
    intersect_kwargs = dict(linestyle=":", alpha=0.4, color=kwargs.get("color"))
    if "x" in project_end_point:
        ax.plot((0, xs[-1]), (ys[-1], ys[-1]), **intersect_kwargs)
    if "y" in project_end_point:
        ax.plot((xs[-1], xs[-1]), (0, ys[-1]), **intersect_kwargs)

    ax.set(ylim=(0, 100), ylabel=f"{metric.title()} (%)")

    # optimal recall line finds all stable materials without any false positives
    # can be included to confirm all models start out of with near optimal recall
    # and to see how much each model overshoots total n_stable
    n_below_hull = sum(e_above_hull_true < 0)
    if show_optimal:
        ax.plot(
            [0, n_below_hull],
            [0, 100],
            color="green",
            linestyle="dashed",
            linewidth=1,
            label=f"Optimal {metric.title()}",
        )
        ax.text(
            n_below_hull,
            100,
            label,
            color=kwargs.get("color"),
            verticalalignment="top",
            rotation=-30,
            bbox=dict(facecolor="white", alpha=0.5, edgecolor="none"),
        )

    return ax


def wandb_scatter(table: wandb.Table, fields: dict[str, str], **kwargs: Any) -> None:
    """Log a parity scatter plot using custom vega spec to WandB.

    Args:
        table (wandb.Table): WandB data table.
        fields (dict[str, str]): Map from table columns to fields defined in the custom
            vega spec. Currently the only Vega fields are 'x' and 'y'.
        **kwargs: Keyword arguments passed to wandb.plot_table(string_fields=kwargs).
    """
    assert set(fields) >= {"x", "y"}, f"{fields=} must specify x and y column names"

    if "form" in fields["x"] and "form" in fields["y"]:
        kwargs.setdefault("x_label", "DFT formation energy (eV/atom)")
        kwargs.setdefault("y_label", "Predicted formation energy (eV/atom)")

    scatter_plot = wandb.plot_table(
        vega_spec_name="janosh/scatter-parity",
        data_table=table,
        fields=fields,
        string_fields=kwargs,
    )

    wandb.log({"true_pred_scatter": scatter_plot})
