"""
Model entrypoint:
- trains (or retrains) the ML pipeline and writes artifacts to ./ml_artifacts
- generates a sample dataset at ./data/sample_dataset.csv if missing
"""

import os

from config import Config
from ml.training import train_and_select_model


def main() -> None:
    dataset_path = os.path.join("data", "sample_dataset.csv")
    artifact_dir = Config.ARTIFACT_DIR

    result = train_and_select_model(dataset_path, artifact_dir)
    print("Training complete")
    print(f"Best model: {result.best_model_name}")
    print(f"Accuracy: {result.best_accuracy:.4f}")
    print(f"Artifacts: {result.artifact_dir}")


if __name__ == "__main__":
    main()

