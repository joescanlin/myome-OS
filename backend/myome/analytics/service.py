"""Main analytics service orchestrating all analysis"""

from datetime import UTC, datetime, timedelta

from myome.analytics.alerts.anomaly import AnomalyDetector
from myome.analytics.alerts.manager import Alert, AlertManager
from myome.analytics.correlation.engine import CorrelationEngine, CorrelationResult
from myome.analytics.correlation.trends import TrendAnalyzer, TrendResult
from myome.analytics.data_loader import TimeSeriesLoader
from myome.core.logging import logger


class AnalyticsService:
    """
    Main service for health data analytics

    Provides high-level interface for:
    - Running daily health analysis
    - Discovering correlations
    - Detecting anomalies
    - Generating insights
    """

    DEFAULT_BIOMARKERS = [
        "heart_rate",
        "hrv_sdnn",
        "hrv_rmssd",
        "glucose",
        "sleep_total",
        "sleep_efficiency",
        "steps",
    ]

    def __init__(self, user_id: str):
        self.user_id = user_id
        self.loader = TimeSeriesLoader(user_id)
        self.correlation_engine = CorrelationEngine(user_id)
        self.anomaly_detector = AnomalyDetector()
        self.trend_analyzer = TrendAnalyzer()
        self.alert_manager = AlertManager(user_id)

    async def run_daily_analysis(
        self,
        analysis_date: datetime | None = None,
    ) -> dict:
        """
        Run comprehensive daily health analysis

        Args:
            analysis_date: Date to analyze (defaults to yesterday)

        Returns:
            Analysis results including alerts, trends, correlations
        """
        if analysis_date is None:
            analysis_date = datetime.now(UTC) - timedelta(days=1)

        # Define analysis windows
        day_start = analysis_date.replace(hour=0, minute=0, second=0)
        day_end = analysis_date.replace(hour=23, minute=59, second=59)
        week_start = day_start - timedelta(days=7)
        month_start = day_start - timedelta(days=30)

        results: dict[str, object] = {
            "date": analysis_date.date().isoformat(),
            "alerts": [],
            "trends": [],
            "correlations": [],
            "daily_summary": {},
        }

        # 1. Anomaly detection for today
        alerts = await self._detect_daily_anomalies(day_start, day_end)
        results["alerts"] = [a.to_dict() for a in alerts]

        # 2. Trend analysis (weekly)
        trends = await self._analyze_trends(week_start, day_end)
        results["trends"] = [t.to_dict() for t in trends]

        # 3. Correlation discovery (monthly)
        correlations = await self._discover_correlations(month_start, day_end)
        results["correlations"] = [c.to_dict() for c in correlations[:10]]  # Top 10

        # 4. Daily summary statistics
        summary = await self._compute_daily_summary(day_start, day_end)
        results["daily_summary"] = summary

        logger.info(
            f"Daily analysis complete for user {self.user_id}: "
            f"{len(alerts)} alerts, {len(trends)} trends, {len(correlations)} correlations"
        )

        return results

    async def _detect_daily_anomalies(
        self,
        start: datetime,
        end: datetime,
    ) -> list[Alert]:
        """Detect anomalies for the day"""
        alerts = []

        # Load each biomarker and check for anomalies
        biomarker_loaders = {
            "heart_rate": self.loader.load_heart_rate,
            "glucose": self.loader.load_glucose,
            "hrv": self.loader.load_hrv,
        }

        for biomarker, loader in biomarker_loaders.items():
            try:
                df = await loader(start, end)
                if df.empty:
                    continue

                # Get the value column
                if biomarker == "heart_rate":
                    series = df["heart_rate_bpm"]
                elif biomarker == "glucose":
                    series = df["glucose_mg_dl"]
                elif biomarker == "hrv":
                    if "sdnn_ms" in df.columns:
                        series = df["sdnn_ms"]
                        biomarker = "hrv_sdnn"  # Use specific name
                    else:
                        continue
                else:
                    continue

                anomalies = self.anomaly_detector.detect_anomalies(series, biomarker)

                for anomaly in anomalies:
                    alert = self.alert_manager.create_alert(anomaly)
                    if alert:
                        alerts.append(alert)

            except Exception as e:
                logger.error(f"Error detecting anomalies for {biomarker}: {e}")

        return alerts

    async def _analyze_trends(
        self,
        start: datetime,
        end: datetime,
    ) -> list[TrendResult]:
        """Analyze trends for all biomarkers"""
        trends: list[TrendResult] = []

        # Load multi-biomarker data
        df = await self.loader.load_multi_biomarker(
            start,
            end,
            biomarkers=["heart_rate", "hrv_sdnn", "glucose"],
            resample="1D",
        )

        if df.empty:
            return trends

        for column in df.columns:
            try:
                trend = self.trend_analyzer.compute_trend(df[column], column)
                if trend and trend.is_significant:
                    trends.append(trend)
            except Exception as e:
                logger.error(f"Error analyzing trend for {column}: {e}")

        return trends

    async def _discover_correlations(
        self,
        start: datetime,
        end: datetime,
    ) -> list[CorrelationResult]:
        """Discover significant correlations"""
        try:
            correlations = await self.correlation_engine.discover_all_correlations(
                biomarkers=["heart_rate", "hrv_sdnn", "glucose"],
                start=start,
                end=end,
            )
            return correlations
        except Exception as e:
            logger.error(f"Error discovering correlations: {e}")
            return []

    async def _compute_daily_summary(
        self,
        start: datetime,
        end: datetime,
    ) -> dict:
        """Compute summary statistics for the day"""
        summary: dict[str, object] = {}

        # Heart rate
        hr_df = await self.loader.load_heart_rate(start, end)
        if not hr_df.empty:
            summary["heart_rate"] = {
                "mean": float(hr_df["heart_rate_bpm"].mean()),
                "min": int(hr_df["heart_rate_bpm"].min()),
                "max": int(hr_df["heart_rate_bpm"].max()),
            }

        # Glucose
        glucose_df = await self.loader.load_glucose(start, end)
        if not glucose_df.empty:
            glucose = glucose_df["glucose_mg_dl"]
            time_in_range = ((glucose >= 70) & (glucose <= 180)).mean() * 100
            summary["glucose"] = {
                "mean": float(glucose.mean()),
                "min": float(glucose.min()),
                "max": float(glucose.max()),
                "time_in_range_pct": float(time_in_range),
            }

        # HRV
        hrv_df = await self.loader.load_hrv(start, end)
        if not hrv_df.empty:
            summary["hrv"] = {
                "sdnn_mean": (
                    float(hrv_df["sdnn_ms"].mean()) if "sdnn_ms" in hrv_df else None
                ),
                "rmssd_mean": (
                    float(hrv_df["rmssd_ms"].mean()) if "rmssd_ms" in hrv_df else None
                ),
            }

        # Sleep (from previous night)
        sleep_df = await self.loader.load_sleep(start - timedelta(days=1), end)
        if not sleep_df.empty:
            latest = sleep_df.iloc[-1]
            summary["sleep"] = {
                "total_minutes": int(latest.get("total_sleep_minutes", 0)),
                "deep_minutes": int(latest.get("deep_sleep_minutes", 0)),
                "efficiency_pct": float(latest.get("sleep_efficiency_pct", 0)),
            }

        return summary

    async def get_health_score(
        self,
        date: datetime | None = None,
    ) -> dict:
        """
        Compute overall health score based on multiple factors

        Returns score 0-100 with component breakdown
        """
        if date is None:
            date = datetime.now(UTC)

        start = date - timedelta(days=7)

        scores: dict[str, float] = {}
        weights: dict[str, float] = {}

        # HRV score (autonomic health)
        hrv_df = await self.loader.load_hrv(start, date)
        if not hrv_df.empty and "rmssd_ms" in hrv_df:
            rmssd = hrv_df["rmssd_ms"].mean()
            # Score based on typical ranges (higher is better)
            if rmssd >= 50:
                scores["hrv"] = 100.0
            elif rmssd >= 30:
                scores["hrv"] = 70.0 + (rmssd - 30) * 1.5
            else:
                scores["hrv"] = max(0.0, rmssd * 2.3)
            weights["hrv"] = 0.25

        # Sleep score
        sleep_df = await self.loader.load_sleep(start, date)
        if not sleep_df.empty:
            avg_duration = float(sleep_df["total_sleep_minutes"].mean())
            avg_efficiency = float(sleep_df["sleep_efficiency_pct"].mean())

            # Duration score (target 7-9 hours = 420-540 minutes)
            if 420 <= avg_duration <= 540:
                duration_score = 100.0
            elif avg_duration < 420:
                duration_score = max(0.0, avg_duration / 420 * 100)
            else:
                duration_score = max(0.0, 100 - (avg_duration - 540) / 2)

            scores["sleep"] = (duration_score + avg_efficiency) / 2
            weights["sleep"] = 0.25

        # Glucose stability (if CGM data available)
        glucose_df = await self.loader.load_glucose(start, date)
        if not glucose_df.empty:
            cv = (
                glucose_df["glucose_mg_dl"].std()
                / glucose_df["glucose_mg_dl"].mean()
                * 100
            )
            tir = (
                (glucose_df["glucose_mg_dl"] >= 70)
                & (glucose_df["glucose_mg_dl"] <= 180)
            ).mean() * 100
            scores["glucose"] = tir - min(cv, 30)  # Penalize high variability
            weights["glucose"] = 0.25

        # Resting heart rate trend
        hr_df = await self.loader.load_heart_rate(start, date, resample="1D")
        if not hr_df.empty:
            rhr = hr_df["heart_rate_bpm"].min()  # Approximation of RHR
            # Lower RHR generally better (within reason)
            if rhr <= 60:
                scores["rhr"] = 100
            elif rhr <= 80:
                scores["rhr"] = 100 - (rhr - 60) * 2
            else:
                scores["rhr"] = max(0, 60 - (rhr - 80) * 2)
            weights["rhr"] = 0.25

        # Calculate weighted average
        if not scores:
            return {"score": None, "components": {}}

        total_weight = sum(weights.values())
        overall_score = sum(scores[k] * weights[k] for k in scores) / total_weight

        return {
            "score": round(overall_score, 1),
            "components": {k: round(v, 1) for k, v in scores.items()},
            "weights": weights,
        }
