from __future__ import annotations

from config import get_settings
from ml import train_and_save_model


def main() -> None:
    settings = get_settings()
    results = train_and_save_model(settings)

    print("Training complete.")
    print(f"Cleaned rows: {results['cleaned_rows']}")
    print(f"Model saved to: {settings.model_path}")
    print(f"Metrics saved to: {settings.metrics_path}")
    print(f"MAE: {results['metrics']['mae']}")
    print(f"RMSE: {results['metrics']['rmse']}")
    print(f"R2: {results['metrics']['r2']}")


if __name__ == "__main__":
    main()
