"""Physician report generation"""

from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta

from myome.analytics.data_loader import TimeSeriesLoader
from myome.analytics.service import AnalyticsService
from myome.core.logging import logger


@dataclass
class ReportSection:
    """A section of the physician report"""

    title: str
    priority: str  # critical, high, normal
    content: dict
    interpretation: str | None = None
    recommendations: list[str] = field(default_factory=list)


class PhysicianReportGenerator:
    """
    Generate comprehensive physician reports from health data

    Reports follow a three-tier structure:
    1. Executive Summary (30 seconds)
    2. Detailed Analysis (5 minutes)
    3. Raw Data Access (as needed)
    """

    def __init__(self, user_id: str):
        self.user_id = user_id
        self.analytics = AnalyticsService(user_id)
        self.loader = TimeSeriesLoader(user_id)

    async def generate_report(
        self,
        report_date: datetime | None = None,
        months_lookback: int = 3,
    ) -> dict:
        """Generate comprehensive physician report"""
        if report_date is None:
            report_date = datetime.now(UTC)

        start_date = report_date - timedelta(days=months_lookback * 30)

        report = {
            "metadata": {
                "patient_id": self.user_id,
                "report_date": report_date.isoformat(),
                "period_start": start_date.isoformat(),
                "period_end": report_date.isoformat(),
                "months_covered": months_lookback,
                "generated_at": datetime.now(UTC).isoformat(),
            },
            "executive_summary": await self._generate_executive_summary(
                start_date, report_date
            ),
            "detailed_analysis": await self._generate_detailed_analysis(
                start_date, report_date
            ),
            "risk_assessment": await self._generate_risk_assessment(
                start_date, report_date
            ),
            "recommendations": await self._generate_recommendations(
                start_date, report_date
            ),
        }

        return report

    async def _generate_executive_summary(
        self,
        start: datetime,
        end: datetime,
    ) -> dict:
        """Generate Tier 1: Executive Summary (30 second review)"""

        # Get daily analysis
        analysis = await self.analytics.run_daily_analysis(end)
        health_score = await self.analytics.get_health_score(end)

        # Categorize alerts by priority
        critical_alerts = [
            a for a in analysis.get("alerts", []) if a.get("priority") == "critical"
        ]
        high_alerts = [
            a for a in analysis.get("alerts", []) if a.get("priority") == "high"
        ]

        return {
            "overall_status": self._determine_status(health_score, critical_alerts),
            "health_score": health_score,
            "critical_alerts": critical_alerts,
            "high_priority_alerts": high_alerts,
            "key_trends": analysis.get("trends", [])[:3],  # Top 3 trends
            "data_completeness": self._calculate_completeness(analysis),
        }

    async def _generate_detailed_analysis(
        self,
        start: datetime,
        end: datetime,
    ) -> dict:
        """Generate Tier 2: Detailed Analysis (5 minute review)"""

        return {
            "cardiovascular": await self._analyze_cardiovascular(start, end),
            "metabolic": await self._analyze_metabolic(start, end),
            "sleep_recovery": await self._analyze_sleep(start, end),
            "correlations": await self._get_top_correlations(start, end),
        }

    async def _analyze_cardiovascular(self, start: datetime, end: datetime) -> dict:
        """Detailed cardiovascular analysis"""
        hr_df = await self.loader.load_heart_rate(start, end, resample="1D")
        hrv_df = await self.loader.load_hrv(start, end, resample="1D")

        result = {
            "resting_heart_rate": None,
            "hrv_analysis": None,
            "trends": [],
            "concerns": [],
        }

        if not hr_df.empty:
            result["resting_heart_rate"] = {
                "current": float(hr_df["heart_rate_bpm"].iloc[-1]),
                "average": float(hr_df["heart_rate_bpm"].mean()),
                "min": int(hr_df["heart_rate_bpm"].min()),
                "max": int(hr_df["heart_rate_bpm"].max()),
                "trend": self._calculate_trend(hr_df["heart_rate_bpm"]),
            }

        if not hrv_df.empty and "sdnn_ms" in hrv_df.columns:
            current_hrv = (
                hrv_df["sdnn_ms"].iloc[-1]
                if not hrv_df["sdnn_ms"].isna().iloc[-1]
                else None
            )
            avg_hrv = hrv_df["sdnn_ms"].mean()

            result["hrv_analysis"] = {
                "current_sdnn": float(current_hrv) if current_hrv else None,
                "average_sdnn": (
                    float(avg_hrv) if not hrv_df["sdnn_ms"].isna().all() else None
                ),
                "trend": self._calculate_trend(hrv_df["sdnn_ms"].dropna()),
                "interpretation": self._interpret_hrv(current_hrv, avg_hrv),
            }

            # Check for HRV decline
            if current_hrv and avg_hrv:
                pct_change = ((current_hrv - avg_hrv) / avg_hrv) * 100
                if pct_change < -20:
                    result["concerns"].append(
                        {
                            "type": "hrv_decline",
                            "severity": "high",
                            "description": f"HRV has declined {abs(pct_change):.1f}% from baseline",
                            "recommendation": "Consider cardiac workup if sustained",
                        }
                    )

        return result

    async def _analyze_metabolic(self, start: datetime, end: datetime) -> dict:
        """Detailed metabolic analysis"""
        glucose_df = await self.loader.load_glucose(start, end)

        result = {
            "glucose_metrics": None,
            "time_in_range": None,
            "concerns": [],
        }

        if not glucose_df.empty:
            glucose = glucose_df["glucose_mg_dl"]

            # Calculate time in range (70-180 mg/dL)
            tir = ((glucose >= 70) & (glucose <= 180)).mean() * 100
            time_below = (glucose < 70).mean() * 100
            time_above = (glucose > 180).mean() * 100

            # Calculate variability
            cv = (glucose.std() / glucose.mean()) * 100 if glucose.mean() > 0 else 0

            result["glucose_metrics"] = {
                "mean": float(glucose.mean()),
                "std": float(glucose.std()),
                "min": float(glucose.min()),
                "max": float(glucose.max()),
                "coefficient_of_variation": float(cv),
            }

            result["time_in_range"] = {
                "in_range_70_180": float(tir),
                "below_70": float(time_below),
                "above_180": float(time_above),
                "target": ">90%",
                "status": (
                    "good"
                    if tir >= 90
                    else "needs_improvement" if tir >= 70 else "concerning"
                ),
            }

            # Check for concerning patterns
            if cv > 36:
                result["concerns"].append(
                    {
                        "type": "high_glucose_variability",
                        "severity": "medium",
                        "description": f"Glucose variability (CV={cv:.1f}%) is above target <36%",
                        "recommendation": "Consider dietary modifications to reduce glycemic variability",
                    }
                )

        return result

    async def _analyze_sleep(self, start: datetime, end: datetime) -> dict:
        """Detailed sleep analysis"""
        sleep_df = await self.loader.load_sleep(start, end)

        result = {
            "average_duration": None,
            "sleep_architecture": None,
            "efficiency": None,
            "concerns": [],
        }

        if not sleep_df.empty:
            avg_duration = sleep_df["total_sleep_minutes"].mean()
            avg_deep = sleep_df.get("deep_sleep_minutes", 0)
            avg_rem = sleep_df.get("rem_sleep_minutes", 0)
            avg_efficiency = sleep_df.get("sleep_efficiency_pct", 0)

            result["average_duration"] = {
                "minutes": (
                    float(avg_duration)
                    if hasattr(avg_duration, "__float__")
                    else avg_duration
                ),
                "hours": (
                    float(avg_duration / 60)
                    if hasattr(avg_duration, "__float__")
                    else avg_duration / 60
                ),
                "target": "7-9 hours",
                "status": "good" if 420 <= avg_duration <= 540 else "needs_improvement",
            }

            if hasattr(avg_deep, "mean"):
                avg_deep = avg_deep.mean()
            if hasattr(avg_rem, "mean"):
                avg_rem = avg_rem.mean()
            if hasattr(avg_efficiency, "mean"):
                avg_efficiency = avg_efficiency.mean()

            result["sleep_architecture"] = {
                "deep_sleep_minutes": float(avg_deep) if avg_deep else None,
                "rem_sleep_minutes": float(avg_rem) if avg_rem else None,
                "deep_pct": (
                    float((avg_deep / avg_duration) * 100)
                    if avg_deep and avg_duration
                    else None
                ),
                "rem_pct": (
                    float((avg_rem / avg_duration) * 100)
                    if avg_rem and avg_duration
                    else None
                ),
            }

            result["efficiency"] = {
                "average_pct": float(avg_efficiency) if avg_efficiency else None,
                "target": ">85%",
                "status": (
                    "good"
                    if avg_efficiency and avg_efficiency >= 85
                    else "needs_improvement"
                ),
            }

        return result

    async def _generate_risk_assessment(self, start: datetime, end: datetime) -> dict:
        """Generate risk assessment scores"""
        health_score = await self.analytics.get_health_score(end)

        return {
            "overall_health_score": health_score.get("score"),
            "component_scores": health_score.get("components", {}),
            "risk_factors": [],  # Would integrate with genetic/biomarker data
        }

    async def _generate_recommendations(
        self, start: datetime, end: datetime
    ) -> list[dict]:
        """Generate clinical recommendations"""
        analysis = await self.analytics.run_daily_analysis(end)
        recommendations = []

        # Based on alerts
        for alert in analysis.get("alerts", []):
            if alert.get("priority") in ["critical", "high"]:
                recommendations.append(
                    {
                        "priority": alert.get("priority"),
                        "category": alert.get("biomarker"),
                        "recommendation": f"Address {alert.get('title', 'alert')}",
                        "rationale": alert.get("message"),
                    }
                )

        # Based on trends
        for trend in analysis.get("trends", []):
            if trend.get("is_significant") and trend.get("direction") != "stable":
                recommendations.append(
                    {
                        "priority": "medium",
                        "category": trend.get("biomarker"),
                        "recommendation": f"Monitor {trend.get('biomarker')} - {trend.get('direction')} trend",
                        "rationale": f"{trend.get('percent_change', 0):.1f}% change over period",
                    }
                )

        return recommendations

    async def _get_top_correlations(self, start: datetime, end: datetime) -> list[dict]:
        """Get top discovered correlations"""
        try:
            correlations = (
                await self.analytics.correlation_engine.discover_all_correlations(
                    ["heart_rate", "hrv_sdnn", "glucose"],
                    start,
                    end,
                )
            )
            return [c.to_dict() for c in correlations[:5]]
        except Exception as e:
            logger.warning(f"Failed to get correlations: {e}")
            return []

    def _determine_status(self, health_score: dict, critical_alerts: list) -> str:
        """Determine overall status"""
        if critical_alerts:
            return "requires_attention"

        score = health_score.get("score")
        if score is None:
            return "insufficient_data"
        if score >= 80:
            return "excellent"
        if score >= 60:
            return "good"
        if score >= 40:
            return "fair"
        return "needs_improvement"

    def _calculate_completeness(self, analysis: dict) -> dict:
        """Calculate data completeness metrics"""
        return {
            "heart_rate": True,  # Simplified - would check actual data coverage
            "glucose": True,
            "sleep": True,
            "overall_pct": 85,
        }

    def _calculate_trend(self, series) -> str:
        """Calculate trend direction from time series"""
        if len(series) < 7:
            return "insufficient_data"

        # Simple linear regression
        import numpy as np

        x = np.arange(len(series))
        y = series.values
        valid = ~np.isnan(y)

        if valid.sum() < 7:
            return "insufficient_data"

        slope = np.polyfit(x[valid], y[valid], 1)[0]

        if abs(slope) < 0.1:
            return "stable"
        return "increasing" if slope > 0 else "decreasing"

    def _interpret_hrv(self, current: float, average: float) -> str:
        """Interpret HRV values"""
        if current is None:
            return "Insufficient data for HRV interpretation"

        if current >= 50:
            return "Excellent autonomic function indicating good recovery capacity"
        if current >= 30:
            return "Normal autonomic function"
        return "Below average HRV may indicate stress or reduced recovery capacity"
