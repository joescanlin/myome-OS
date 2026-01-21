"""Glucose response prediction model"""

from dataclasses import dataclass
from datetime import datetime, timedelta

import joblib
import numpy as np
from sklearn.ensemble import GradientBoostingRegressor
from sklearn.model_selection import cross_val_score

from myome.analytics.data_loader import TimeSeriesLoader
from myome.core.logging import logger


@dataclass
class GlucosePrediction:
    """Predicted glucose response"""

    predicted_peak_mg_dl: float
    predicted_time_to_peak_minutes: int
    confidence_interval: tuple[float, float]
    contributing_factors: dict[str, float]


@dataclass
class MealContext:
    """Context for glucose prediction"""

    carbohydrates_g: float
    fiber_g: float
    protein_g: float
    fat_g: float
    glycemic_load: float | None
    time_of_day: datetime
    hours_since_wake: float
    recent_exercise_minutes: int
    sleep_quality_score: float | None
    baseline_glucose: float


class GlucoseResponsePredictor:
    """
    Predict postprandial glucose response

    Uses gradient boosted trees trained on historical meal/glucose data
    to predict glucose peak after eating.
    """

    def __init__(self, user_id: str):
        self.user_id = user_id
        self.loader = TimeSeriesLoader(user_id)
        self.model: GradientBoostingRegressor | None = None
        self.feature_names: list[str] = []
        self._is_trained = False

    def _extract_features(self, meal: MealContext) -> np.ndarray:
        """Convert meal context to feature vector"""
        features = {
            "carbs_g": meal.carbohydrates_g,
            "fiber_g": meal.fiber_g,
            "protein_g": meal.protein_g,
            "fat_g": meal.fat_g,
            "glycemic_load": meal.glycemic_load or 0,
            "hour_of_day": meal.time_of_day.hour,
            "hours_since_wake": meal.hours_since_wake,
            "recent_exercise_min": meal.recent_exercise_minutes,
            "sleep_quality": meal.sleep_quality_score or 0,
            "baseline_glucose": meal.baseline_glucose,
            "carb_fiber_ratio": meal.carbohydrates_g / max(meal.fiber_g, 1),
            "is_morning": 1 if meal.time_of_day.hour < 12 else 0,
            "is_evening": 1 if meal.time_of_day.hour >= 18 else 0,
        }

        self.feature_names = list(features.keys())
        return np.array(list(features.values()))

    async def train(
        self,
        start: datetime,
        end: datetime,
        meal_logs: list[dict],
    ) -> dict:
        """
        Train model on historical meal and glucose data

        Args:
            start: Training data start
            end: Training data end
            meal_logs: List of meal logs with macro info

        Returns:
            Training metrics
        """
        # Load glucose data
        glucose_df = await self.loader.load_glucose(start, end)

        if glucose_df.empty or len(meal_logs) < 10:
            logger.warning("Insufficient data for training glucose predictor")
            return {"error": "insufficient_data"}

        X: list[np.ndarray] = []
        y: list[float] = []

        for meal in meal_logs:
            meal_time = meal["timestamp"]

            # Find glucose peak in 2-hour window after meal
            window_start = meal_time
            window_end = meal_time + timedelta(hours=2)

            meal_glucose = glucose_df[
                (glucose_df.index >= window_start) & (glucose_df.index <= window_end)
            ]

            if meal_glucose.empty:
                continue

            peak_glucose = meal_glucose["glucose_mg_dl"].max()
            baseline = (
                meal_glucose["glucose_mg_dl"].iloc[0] if len(meal_glucose) > 0 else 100
            )

            # Create context
            context = MealContext(
                carbohydrates_g=meal.get("carbs", 0),
                fiber_g=meal.get("fiber", 0),
                protein_g=meal.get("protein", 0),
                fat_g=meal.get("fat", 0),
                glycemic_load=meal.get("glycemic_load"),
                time_of_day=meal_time,
                hours_since_wake=meal.get("hours_since_wake", 2),
                recent_exercise_minutes=meal.get("recent_exercise", 0),
                sleep_quality_score=meal.get("sleep_quality"),
                baseline_glucose=baseline,
            )

            features = self._extract_features(context)
            X.append(features)
            y.append(peak_glucose)

        if len(X) < 10:
            return {"error": "insufficient_training_samples"}

        X_array = np.array(X)
        y_array = np.array(y)

        # Train model
        self.model = GradientBoostingRegressor(
            n_estimators=100,
            max_depth=4,
            learning_rate=0.1,
            random_state=42,
        )

        # Cross-validation
        cv_scores = cross_val_score(
            self.model, X_array, y_array, cv=5, scoring="neg_mean_squared_error"
        )
        rmse = np.sqrt(-cv_scores.mean())

        # Final fit
        self.model.fit(X_array, y_array)
        self._is_trained = True

        # Feature importance
        importance = dict(zip(self.feature_names, self.model.feature_importances_))

        return {
            "n_samples": len(X_array),
            "rmse": float(rmse),
            "r2": float(self.model.score(X_array, y_array)),
            "feature_importance": importance,
        }

    def predict(self, meal: MealContext) -> GlucosePrediction | None:
        """
        Predict glucose response for a meal

        Args:
            meal: Meal context with macros and timing

        Returns:
            Predicted glucose peak and confidence interval
        """
        if not self._is_trained or self.model is None:
            return None

        features = self._extract_features(meal).reshape(1, -1)

        # Point prediction
        predicted_peak = self.model.predict(features)[0]

        # Estimate confidence interval using training variance
        # (simplified - production would use quantile regression)
        std_estimate = 15  # mg/dL typical prediction uncertainty
        ci_lower = predicted_peak - 1.96 * std_estimate
        ci_upper = predicted_peak + 1.96 * std_estimate

        # Feature contributions
        contributions = dict(
            zip(self.feature_names, features[0] * self.model.feature_importances_)
        )

        return GlucosePrediction(
            predicted_peak_mg_dl=float(predicted_peak),
            predicted_time_to_peak_minutes=60,  # Typical
            confidence_interval=(float(ci_lower), float(ci_upper)),
            contributing_factors=contributions,
        )

    def save(self, path: str) -> None:
        """Save trained model to file"""
        if self.model is not None:
            joblib.dump(
                {
                    "model": self.model,
                    "feature_names": self.feature_names,
                },
                path,
            )

    def load(self, path: str) -> None:
        """Load trained model from file"""
        data = joblib.load(path)
        self.model = data["model"]
        self.feature_names = data["feature_names"]
        self._is_trained = True
