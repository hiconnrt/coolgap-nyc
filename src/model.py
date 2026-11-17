"""Phase 4, step 2: train a model to predict surface temperature.

Run from the coolgap folder (after python -m src.satellite):
    python -m src.model

The model is a Random Forest. It is a supervised machine learning model:
it is shown many grid cells where the answer (surface temperature) is
known, and it learns rules that connect the features to the answer. A
Random Forest is many decision trees that each make a guess. The average
of their guesses is the prediction.

Features (inputs) for each 100 m cell:
    ndvi, ndbi, brightness, the same three for the cells around it,
    and coast_distance_m
Target (the answer): surface_temp_f

How it is tested fairly (spatial split):
    Cells next to each other are very similar. If neighbors were split
    randomly between training and testing, the model could "cheat" by
    remembering the cell next door. So the area is cut into 1 km blocks,
    and whole blocks go to either training or testing. The model is scored
    only on blocks it never saw.

    Two tests are reported:
      1. Spatial cross-validation (the main result). The blocks are split
         into 5 groups. Each group takes a turn as the test set while the
         model trains on the other 4. Every cell gets tested exactly once.
      2. One held-out split, where 25% of blocks are set aside.

Surface temperature is how hot the ground and roofs are. It is NOT the air
temperature people feel.
"""
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestRegressor
from sklearn.inspection import permutation_importance
from sklearn.metrics import mean_absolute_error, r2_score
from sklearn.model_selection import (GroupKFold, GroupShuffleSplit,
                                     cross_val_predict, train_test_split)

from src import config

FEATURES = config.MODEL_FEATURES
TARGET = "surface_temp_f"

FEATURE_LABELS = {
    "ndvi": "Greenness of the cell (NDVI)",
    "ndbi": "Built-up index of the cell (NDBI)",
    "brightness": "Brightness of the cell (reflected sunlight)",
    "ndvi_nearby": "Greenness of the cells around it",
    "brightness_nearby": "Brightness of the cells around it",
    "ndbi_nearby": "Built-up index of the cells around it",
    "coast_distance_m": "Distance to the coast",
}


def load_grid() -> pd.DataFrame:
    return pd.read_csv(config.PROCESSED_DIR / "heat_grid.csv")


def new_model() -> RandomForestRegressor:
    return RandomForestRegressor(n_estimators=config.MODEL_TREES, min_samples_leaf=3,
                                 random_state=config.MODEL_SEED, n_jobs=1)


def spatial_blocks(grid: pd.DataFrame) -> pd.Series:
    """Label each cell with the 1 km block it sits in."""
    size = config.MODEL_BLOCK_METERS
    return (grid["x"] // size).astype(int).astype(str) + "_" + (grid["y"] // size).astype(int).astype(str)


def score(actual, predicted) -> dict:
    return {"r2": float(r2_score(actual, predicted)),
            "mae_f": float(mean_absolute_error(actual, predicted))}


def train_and_test(grid: pd.DataFrame) -> dict:
    """Train on some blocks, test on the others, and report how it did."""
    blocks = spatial_blocks(grid)
    splitter = GroupShuffleSplit(n_splits=1, test_size=config.MODEL_TEST_SHARE,
                                 random_state=config.MODEL_SEED)
    train_idx, test_idx = next(splitter.split(grid, groups=blocks))
    train, test = grid.iloc[train_idx], grid.iloc[test_idx]

    model = new_model().fit(train[FEATURES], train[TARGET])
    test_pred = model.predict(test[FEATURES])

    # Main result: spatial cross-validation. Every cell is predicted by a
    # model that never saw its block.
    folds = GroupKFold(n_splits=config.MODEL_CV_FOLDS)
    cv_pred = cross_val_predict(new_model(), grid[FEATURES], grid[TARGET],
                                groups=blocks, cv=folds)
    fold_scores = [score(grid[TARGET].iloc[idx], cv_pred[idx])
                   for _, idx in folds.split(grid, groups=blocks)]
    cv_baseline = np.empty(len(grid))
    for train_fold, test_fold in folds.split(grid, groups=blocks):
        cv_baseline[test_fold] = grid[TARGET].iloc[train_fold].mean()

    # Baseline: always guess the average training temperature.
    baseline_pred = np.full(len(test), train[TARGET].mean())

    # For comparison only: a random split, which lets neighbors leak.
    r_train, r_test = train_test_split(grid, test_size=config.MODEL_TEST_SHARE,
                                       random_state=config.MODEL_SEED)
    random_model = new_model().fit(r_train[FEATURES], r_train[TARGET])

    importance = permutation_importance(model, test[FEATURES], test[TARGET],
                                        n_repeats=20, random_state=config.MODEL_SEED,
                                        scoring="neg_mean_absolute_error")
    importance_table = pd.DataFrame({
        "feature": FEATURES,
        "label": [FEATURE_LABELS[f] for f in FEATURES],
        # How much worse the error gets (in degrees F) when this feature is scrambled.
        "mae_increase_f": importance.importances_mean,
        "tree_importance": model.feature_importances_,
    }).sort_values("mae_increase_f", ascending=False)

    predictions = grid.copy()
    # The prediction kept for each cell is the cross-validation one, so it
    # always comes from a model that did not train on that cell's block.
    predictions["predicted_temp_f"] = cv_pred
    predictions["split"] = "train"
    predictions.iloc[test_idx, predictions.columns.get_loc("split")] = "test"
    predictions["error_f"] = predictions["predicted_temp_f"] - predictions[TARGET]

    return {
        "metrics": {
            "cells_total": len(grid), "cells_train": len(train), "cells_test": len(test),
            "blocks_train": int(blocks.iloc[train_idx].nunique()),
            "blocks_test": int(blocks.iloc[test_idx].nunique()),
            "cv": score(grid[TARGET], cv_pred),
            "cv_folds": fold_scores,
            "cv_baseline": score(grid[TARGET], cv_baseline),
            "temp_min_f": float(grid[TARGET].min()), "temp_max_f": float(grid[TARGET].max()),
            "temp_std_f": float(grid[TARGET].std()),
            "test": score(test[TARGET], test_pred),
            "train": score(train[TARGET], model.predict(train[FEATURES])),
            "baseline_test": score(test[TARGET], baseline_pred),
            "random_split_test": score(r_test[TARGET], random_model.predict(r_test[FEATURES])),
            "test_temp_std_f": float(test[TARGET].std()),
        },
        "importance": importance_table,
        "predictions": predictions,
    }


def main() -> None:
    result = train_and_test(load_grid())
    result["predictions"].to_csv(config.PROCESSED_DIR / "heat_grid_predictions.csv", index=False)
    m = result["metrics"]
    print(f"Cells: {m['cells_total']:,} (train {m['cells_train']:,} in {m['blocks_train']} blocks, "
          f"test {m['cells_test']:,} in {m['blocks_test']} blocks)")
    print(f"SPATIAL CROSS-VALIDATION ({config.MODEL_CV_FOLDS} folds): R squared "
          f"{m['cv']['r2']:.3f}, MAE {m['cv']['mae_f']:.2f} F "
          f"(baseline MAE {m['cv_baseline']['mae_f']:.2f} F)")
    print("  each fold: " + ", ".join(f"R2 {f['r2']:.2f} / MAE {f['mae_f']:.2f}"
                                       for f in m["cv_folds"]))
    print(f"Held-out split (25% of blocks):  R squared {m['test']['r2']:.3f}, MAE {m['test']['mae_f']:.2f} F")
    print(f"Baseline (guess the average): R squared {m['baseline_test']['r2']:.3f}, "
          f"MAE {m['baseline_test']['mae_f']:.2f} F")
    print(f"Training cells: R squared {m['train']['r2']:.3f}, MAE {m['train']['mae_f']:.2f} F")
    print(f"Random split (leaky, for comparison): R squared {m['random_split_test']['r2']:.3f}, "
          f"MAE {m['random_split_test']['mae_f']:.2f} F")
    print(result["importance"].round(3).to_string(index=False))


if __name__ == "__main__":
    main()
