"""Experiment E: how accurate is the block-level surface temperature model?

Run from the coolgap folder (after python -m src.satellite):
    python -m experiments.exp_e_model

Reports R squared and mean absolute error (MAE) on data the model did not
train on, using spatial splits so nearby cells cannot leak.

Reminder: surface temperature is not the air temperature people feel.
"""
import pandas as pd

from experiments import common
from src import config, model


def main() -> None:
    result = model.train_and_test(model.load_grid())
    m, importance, pred = result["metrics"], result["importance"], result["predictions"]
    pred.to_csv(config.PROCESSED_DIR / "heat_grid_predictions.csv", index=False)

    metrics = pd.DataFrame([
        {"test": f"Spatial cross-validation ({config.MODEL_CV_FOLDS} folds), main result",
         "r2": m["cv"]["r2"], "mae_f": m["cv"]["mae_f"]},
        {"test": "Baseline for cross-validation (guess the training average)",
         "r2": m["cv_baseline"]["r2"], "mae_f": m["cv_baseline"]["mae_f"]},
        {"test": "Held-out split (25% of blocks)",
         "r2": m["test"]["r2"], "mae_f": m["test"]["mae_f"]},
        {"test": "Baseline for held-out split",
         "r2": m["baseline_test"]["r2"], "mae_f": m["baseline_test"]["mae_f"]},
        {"test": "Training cells (not a fair test, shown to reveal overfitting)",
         "r2": m["train"]["r2"], "mae_f": m["train"]["mae_f"]},
        {"test": "Random split (leaky, for comparison only)",
         "r2": m["random_split_test"]["r2"], "mae_f": m["random_split_test"]["mae_f"]},
    ] + [{"test": f"Cross-validation fold {i + 1}", "r2": f["r2"], "mae_f": f["mae_f"]}
         for i, f in enumerate(m["cv_folds"])])
    common.save_table(metrics.round(3), "exp_e_metrics.csv")
    common.save_table(importance.round(4), "exp_e_feature_importance.csv")

    fig, ax = common.new_chart(6.2, 6)
    ax.scatter(pred["surface_temp_f"], pred["predicted_temp_f"], s=7, color=common.BLUE,
               alpha=0.35, linewidth=0)
    low, high = pred["surface_temp_f"].min() - 1, pred["surface_temp_f"].max() + 1
    ax.plot([low, high], [low, high], color=common.MUTED, linewidth=1, linestyle="--")
    ax.text(high - 0.5, high - 1.5, "perfect prediction", fontsize=8, color=common.MUTED,
            ha="right", rotation=45)
    ax.set_xlim(low, high), ax.set_ylim(low, high)
    ax.set_xlabel("Measured surface temperature (F)", color=common.INK)
    ax.set_ylabel("Predicted surface temperature (F)", color=common.INK)
    ax.set_title(f"Experiment E: each dot is one 100 m cell\n"
                 f"R squared {m['cv']['r2']:.2f}, average error {m['cv']['mae_f']:.1f} F "
                 "(spatial cross-validation)", fontsize=10, color=common.INK, loc="left")
    common.save_chart(fig, "exp_e_predicted_vs_measured.png")

    fig, ax = common.new_chart(8.5, 4)
    shown = importance.iloc[::-1]
    ax.barh(shown["label"], shown["mae_increase_f"], color=common.BLUE, height=0.6)
    for y, v in enumerate(shown["mae_increase_f"]):
        ax.text(v + 0.01, y, f"{v:.2f} F", va="center", fontsize=9, color=common.INK)
    ax.grid(axis="y", visible=False)
    ax.tick_params(axis="y", labelsize=8, colors=common.INK)
    ax.set_xlim(0, shown["mae_increase_f"].max() * 1.2)
    ax.set_xlabel("How much the error grows (F) when this feature is scrambled", color=common.INK)
    ax.set_title("Experiment E: which features the model relies on",
                 fontsize=11, color=common.INK, loc="left")
    common.save_chart(fig, "exp_e_feature_importance.png")

    lines = [
        "EXPERIMENT E: block-level surface temperature model",
        f"Satellite scene: {config.LANDSAT_ITEM} ({config.LANDSAT_DATE}), USGS Landsat "
        "Collection 2 Level-2 via Microsoft Planetary Computer",
        f"Grid: {m['cells_total']:,} cells of {config.GRID_CELL_METERS} m in {config.FOCUS_NAME}",
        f"Measured surface temperature: {m['temp_min_f']:.1f} to {m['temp_max_f']:.1f} F "
        f"(standard deviation {m['temp_std_f']:.1f} F)",
        f"Model: Random Forest, {config.MODEL_TREES} trees. Features: {', '.join(config.MODEL_FEATURES)}",
        f"MAIN RESULT, spatial cross-validation ({config.MODEL_CV_FOLDS} folds of "
        f"{config.MODEL_BLOCK_METERS} m blocks): R squared {m['cv']['r2']:.3f}, "
        f"MAE {m['cv']['mae_f']:.2f} F",
        f"Baseline (guess the training average): MAE {m['cv_baseline']['mae_f']:.2f} F",
        "Each fold: " + "; ".join(f"R squared {f['r2']:.2f}, MAE {f['mae_f']:.2f} F"
                                  for f in m["cv_folds"]),
        f"Held-out split (25% of blocks, {m['cells_test']} cells in {m['blocks_test']} blocks): "
        f"R squared {m['test']['r2']:.3f}, MAE {m['test']['mae_f']:.2f} F "
        f"(baseline MAE {m['baseline_test']['mae_f']:.2f} F)",
        f"Training cells: R squared {m['train']['r2']:.3f}, MAE {m['train']['mae_f']:.2f} F",
        f"Random split (leaky, comparison only): R squared {m['random_split_test']['r2']:.3f}, "
        f"MAE {m['random_split_test']['mae_f']:.2f} F",
        "Feature importance (error growth in F when scrambled): "
        + "; ".join(f"{r['label']} {r['mae_increase_f']:.2f}" for _, r in importance.iterrows()),
        "Note: an earlier version without the two brightness features scored lower "
        "(spatial cross-validation R squared 0.34). Brightness was added after seeing that.",
        "Surface temperature is not the air temperature people feel.",
    ]
    common.save_summary(lines, "exp_e_summary.txt")


if __name__ == "__main__":
    main()
