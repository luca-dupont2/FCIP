"""Train prediction models using data from the database (or synthetic)."""
from __future__ import annotations

import sys
from pathlib import Path

from fcip_predictor.trainer import ModelTrainer


def main() -> None:
    model_dir = Path(__file__).parent.parent / "packages" / "predictor" / "models"
    model_dir.mkdir(parents=True, exist_ok=True)

    n_synthetic = int(sys.argv[1]) if len(sys.argv) > 1 else 2000

    trainer = ModelTrainer(model_dir=model_dir, n_synthetic=n_synthetic)
    print(f"Training models with {n_synthetic} synthetic samples...")
    results = trainer.train_all()

    for name, result in results.items():
        print(f"\n{name}:")
        print(f"  Dataset size: {result['dataset_size']}")
        print(f"  Version: {result['version']}")
        print(f"  Accuracy/metrics: {result['metrics']}")
        print(f"  Duration: {result['duration']:.1f}s")
        print(f"  Saved to: {result['file_path']}")

    print("\nTraining complete!")


if __name__ == "__main__":
    main()
