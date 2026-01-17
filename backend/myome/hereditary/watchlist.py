"""Watchlist generator based on family health history"""

from dataclasses import dataclass
from datetime import UTC, datetime


@dataclass
class WatchlistItemConfig:
    """Configuration for a watchlist item"""

    biomarker: str
    display_name: str
    unit: str
    alert_threshold: float
    alert_direction: str  # "above" or "below"
    priority: str  # "critical", "high", "medium", "low"
    family_context: str
    recommendation: str
    contributing_family_member_id: str | None = None


# Biomarker configurations with standard thresholds
BIOMARKER_CONFIGS = {
    "ldl": {
        "display_name": "LDL Cholesterol",
        "unit": "mg/dL",
        "standard_threshold": 130,
        "direction": "above",
        "recommendation_template": "Monitor LDL cholesterol. Consider discussing statin therapy with your physician if levels remain elevated.",
    },
    "hdl": {
        "display_name": "HDL Cholesterol",
        "unit": "mg/dL",
        "standard_threshold": 40,
        "direction": "below",
        "recommendation_template": "Low HDL is a cardiovascular risk factor. Regular exercise and healthy fats can help raise HDL.",
    },
    "total_cholesterol": {
        "display_name": "Total Cholesterol",
        "unit": "mg/dL",
        "standard_threshold": 200,
        "direction": "above",
        "recommendation_template": "Elevated total cholesterol increases cardiovascular risk. Consider lifestyle modifications.",
    },
    "triglycerides": {
        "display_name": "Triglycerides",
        "unit": "mg/dL",
        "standard_threshold": 150,
        "direction": "above",
        "recommendation_template": "High triglycerides can indicate metabolic syndrome risk. Reduce refined carbs and alcohol.",
    },
    "hba1c": {
        "display_name": "HbA1c",
        "unit": "%",
        "standard_threshold": 5.7,
        "direction": "above",
        "recommendation_template": "Elevated HbA1c suggests pre-diabetes risk. Monitor glucose closely and optimize diet.",
    },
    "fasting_glucose": {
        "display_name": "Fasting Glucose",
        "unit": "mg/dL",
        "standard_threshold": 100,
        "direction": "above",
        "recommendation_template": "Elevated fasting glucose indicates diabetes risk. Consider CGM monitoring and dietary changes.",
    },
    "blood_pressure_systolic": {
        "display_name": "Systolic Blood Pressure",
        "unit": "mmHg",
        "standard_threshold": 130,
        "direction": "above",
        "recommendation_template": "Monitor blood pressure regularly. Consider DASH diet and sodium reduction.",
    },
    "blood_pressure_diastolic": {
        "display_name": "Diastolic Blood Pressure",
        "unit": "mmHg",
        "standard_threshold": 85,
        "direction": "above",
        "recommendation_template": "Elevated diastolic pressure increases stroke risk. Regular monitoring recommended.",
    },
    "heart_rate_resting": {
        "display_name": "Resting Heart Rate",
        "unit": "bpm",
        "standard_threshold": 80,
        "direction": "above",
        "recommendation_template": "Elevated resting heart rate may indicate cardiovascular stress. Consider cardiology evaluation.",
    },
    "hrv_sdnn": {
        "display_name": "Heart Rate Variability (SDNN)",
        "unit": "ms",
        "standard_threshold": 50,
        "direction": "below",
        "recommendation_template": "Low HRV suggests reduced autonomic function. Focus on stress management and sleep quality.",
    },
    "egfr": {
        "display_name": "eGFR (Kidney Function)",
        "unit": "mL/min/1.73m2",
        "standard_threshold": 60,
        "direction": "below",
        "recommendation_template": "Reduced kidney function detected. Nephrology consultation recommended.",
    },
}


class WatchlistGenerator:
    """
    Generate personalized monitoring watchlist from family health data

    Creates alert thresholds calibrated to family history, enabling
    earlier detection of conditions that run in the family.
    """

    def __init__(self, user_age: int):
        self.user_age = user_age

    def generate_watchlist(
        self,
        family_members: list,
    ) -> list[WatchlistItemConfig]:
        """
        Generate watchlist items from family member health data

        Args:
            family_members: List of FamilyMember objects
        """
        watchlist = []

        # Collect all family biomarkers and conditions
        family_biomarkers = self._aggregate_family_biomarkers(family_members)
        family_conditions = self._aggregate_family_conditions(family_members)

        # Generate watchlist items for biomarkers
        for biomarker_name, family_data in family_biomarkers.items():
            item = self._create_biomarker_watchlist_item(
                biomarker_name,
                family_data,
            )
            if item:
                watchlist.append(item)

        # Generate watchlist items for conditions
        for condition, relatives in family_conditions.items():
            items = self._create_condition_watchlist_items(condition, relatives)
            watchlist.extend(items)

        # Sort by priority
        priority_order = {"critical": 0, "high": 1, "medium": 2, "low": 3}
        watchlist.sort(key=lambda x: priority_order.get(x.priority, 4))

        return watchlist

    def _aggregate_family_biomarkers(self, family_members: list) -> dict:
        """Aggregate biomarker data across family members"""
        aggregated = {}

        for member in family_members:
            if not member.biomarkers:
                continue

            for biomarker_name, data in member.biomarkers.items():
                if biomarker_name not in aggregated:
                    aggregated[biomarker_name] = []

                aggregated[biomarker_name].append(
                    {
                        "value": data.get("value"),
                        "age_at_measurement": data.get("age_at_measurement"),
                        "is_abnormal": data.get("is_abnormal"),
                        "relationship": member.relationship,
                        "relatedness": member.relatedness,
                        "member_id": member.id,
                    }
                )

        return aggregated

    def _aggregate_family_conditions(self, family_members: list) -> dict:
        """Aggregate conditions across family members"""
        aggregated = {}

        for member in family_members:
            if not member.conditions:
                continue

            for condition_data in member.conditions:
                condition = condition_data.get("condition")
                if not condition:
                    continue

                if condition not in aggregated:
                    aggregated[condition] = []

                aggregated[condition].append(
                    {
                        "onset_age": condition_data.get("onset_age"),
                        "current": condition_data.get("current", True),
                        "relationship": member.relationship,
                        "relatedness": member.relatedness,
                        "member_id": member.id,
                    }
                )

        return aggregated

    def _create_biomarker_watchlist_item(
        self,
        biomarker_name: str,
        family_data: list[dict],
    ) -> WatchlistItemConfig | None:
        """Create watchlist item for a biomarker based on family data"""
        config = BIOMARKER_CONFIGS.get(biomarker_name)
        if not config:
            return None

        # Find the most concerning family member data
        most_relevant = None
        highest_concern = 0

        for data in family_data:
            if data.get("value") is None:
                continue

            # Calculate concern score based on:
            # 1. Relatedness (closer = more concerning)
            # 2. Whether value was abnormal
            # 3. Age at measurement relative to user's current age
            concern = data["relatedness"]

            if data.get("is_abnormal"):
                concern *= 1.5

            age_at_measurement = data.get("age_at_measurement")
            if age_at_measurement and age_at_measurement <= self.user_age + 10:
                concern *= (
                    1.3  # More concerning if relative had issue near user's current age
                )

            if concern > highest_concern:
                highest_concern = concern
                most_relevant = data

        if not most_relevant:
            return None

        # Calculate personalized threshold
        family_value = most_relevant["value"]
        standard_threshold = config["standard_threshold"]
        direction = config["direction"]

        if direction == "above":
            # Set threshold at 80% of family member's value if lower than standard
            personalized_threshold = min(family_value * 0.80, standard_threshold)
        else:  # below
            # Set threshold at 120% of family member's value if higher than standard
            personalized_threshold = max(family_value * 1.20, standard_threshold)

        # Determine priority
        priority = self._determine_priority(
            most_relevant["relatedness"], most_relevant.get("is_abnormal")
        )

        # Generate context
        age_info = (
            f" at age {most_relevant['age_at_measurement']}"
            if most_relevant.get("age_at_measurement")
            else ""
        )
        context = (
            f"Your {most_relevant['relationship']} had {config['display_name']} of "
            f"{family_value} {config['unit']}{age_info}."
        )

        return WatchlistItemConfig(
            biomarker=biomarker_name,
            display_name=config["display_name"],
            unit=config["unit"],
            alert_threshold=round(personalized_threshold, 1),
            alert_direction=direction,
            priority=priority,
            family_context=context,
            recommendation=config["recommendation_template"],
            contributing_family_member_id=most_relevant.get("member_id"),
        )

    def _create_condition_watchlist_items(
        self,
        condition: str,
        relatives: list[dict],
    ) -> list[WatchlistItemConfig]:
        """Create watchlist items for biomarkers related to a condition"""
        items = []

        # Condition to biomarker mapping
        condition_biomarkers = {
            "type_2_diabetes": ["hba1c", "fasting_glucose"],
            "type_1_diabetes": ["hba1c", "fasting_glucose"],
            "hypertension": ["blood_pressure_systolic", "blood_pressure_diastolic"],
            "hyperlipidemia": ["ldl", "total_cholesterol", "triglycerides"],
            "coronary_artery_disease": [
                "ldl",
                "blood_pressure_systolic",
                "heart_rate_resting",
            ],
            "myocardial_infarction": [
                "ldl",
                "blood_pressure_systolic",
                "heart_rate_resting",
                "hrv_sdnn",
            ],
            "stroke": ["blood_pressure_systolic", "blood_pressure_diastolic"],
            "atrial_fibrillation": ["heart_rate_resting", "hrv_sdnn"],
            "chronic_kidney_disease": ["egfr"],
        }

        related_biomarkers = condition_biomarkers.get(condition, [])

        # Find earliest onset in family
        earliest_onset = None
        earliest_relative = None
        closest_relative = None
        highest_relatedness = 0

        for rel in relatives:
            onset = rel.get("onset_age")
            if onset and (earliest_onset is None or onset < earliest_onset):
                earliest_onset = onset
                earliest_relative = rel

            if rel["relatedness"] > highest_relatedness:
                highest_relatedness = rel["relatedness"]
                closest_relative = rel

        # Determine priority based on family history
        first_degree = [r for r in relatives if r["relatedness"] >= 0.5]
        priority = "high" if first_degree else "medium"

        if earliest_onset and earliest_onset < 55:
            priority = "critical" if first_degree else "high"

        # Create watchlist items for related biomarkers
        for biomarker_name in related_biomarkers:
            config = BIOMARKER_CONFIGS.get(biomarker_name)
            if not config:
                continue

            # Generate context
            if earliest_relative:
                onset_text = f" at age {earliest_onset}" if earliest_onset else ""
                context = (
                    f"Your {earliest_relative['relationship']} had {condition.replace('_', ' ')}{onset_text}. "
                    f"Monitoring {config['display_name']} for early detection."
                )
            else:
                context = f"Family history of {condition.replace('_', ' ')}. Monitoring {config['display_name']}."

            # Adjust threshold for early detection
            standard_threshold = config["standard_threshold"]
            if config["direction"] == "above":
                adjusted_threshold = standard_threshold * 0.9  # 10% more aggressive
            else:
                adjusted_threshold = standard_threshold * 1.1

            items.append(
                WatchlistItemConfig(
                    biomarker=biomarker_name,
                    display_name=config["display_name"],
                    unit=config["unit"],
                    alert_threshold=round(adjusted_threshold, 1),
                    alert_direction=config["direction"],
                    priority=priority,
                    family_context=context,
                    recommendation=config["recommendation_template"],
                    contributing_family_member_id=(
                        closest_relative.get("member_id") if closest_relative else None
                    ),
                )
            )

        return items

    def _determine_priority(self, relatedness: float, is_abnormal: bool | None) -> str:
        """Determine watchlist item priority"""
        if relatedness >= 0.5:  # First-degree relative
            return "critical" if is_abnormal else "high"
        elif relatedness >= 0.25:  # Second-degree relative
            return "high" if is_abnormal else "medium"
        else:
            return "medium" if is_abnormal else "low"


class FamilyHistoryPDFGenerator:
    """
    Generate clinical family history document

    Creates a standardized, shareable family health history document
    suitable for doctor visits.
    """

    def generate_summary(
        self,
        user_profile: dict,
        family_members: list,
        watchlist: list[WatchlistItemConfig],
    ) -> dict:
        """
        Generate family history summary document

        Args:
            user_profile: User's basic info (name, age, etc.)
            family_members: List of FamilyMember objects
            watchlist: Generated watchlist items
        """
        # Build pedigree structure
        pedigree = self._build_pedigree(family_members)

        # Summarize conditions
        condition_summary = self._summarize_conditions(family_members)

        # Generate risk summary
        risk_summary = self._summarize_risks(watchlist)

        return {
            "document_type": "family_health_history",
            "generated_at": datetime.now(UTC).isoformat(),
            "patient": {
                "name": user_profile.get("name", ""),
                "age": user_profile.get("age"),
                "biological_sex": user_profile.get("biological_sex"),
            },
            "pedigree": pedigree,
            "conditions_in_family": condition_summary,
            "recommended_monitoring": risk_summary,
            "notes": [
                "This document summarizes family health history for clinical use.",
                "Data sourced from patient-reported information and uploaded documents.",
                "Please verify all information during consultation.",
            ],
        }

    def _build_pedigree(self, family_members: list) -> dict:
        """Build family tree structure"""
        pedigree = {
            "maternal": {
                "grandmother": None,
                "grandfather": None,
                "mother": None,
                "aunts_uncles": [],
            },
            "paternal": {
                "grandmother": None,
                "grandfather": None,
                "father": None,
                "aunts_uncles": [],
            },
            "siblings": [],
            "children": [],
        }

        for member in family_members:
            rel = member.relationship
            summary = {
                "conditions": member.conditions or [],
                "is_living": member.is_living,
                "age_at_death": member.age_at_death,
                "cause_of_death": member.cause_of_death,
            }

            if rel == "mother":
                pedigree["maternal"]["mother"] = summary
            elif rel == "father":
                pedigree["paternal"]["father"] = summary
            elif rel == "maternal_grandmother":
                pedigree["maternal"]["grandmother"] = summary
            elif rel == "maternal_grandfather":
                pedigree["maternal"]["grandfather"] = summary
            elif rel == "paternal_grandmother":
                pedigree["paternal"]["grandmother"] = summary
            elif rel == "paternal_grandfather":
                pedigree["paternal"]["grandfather"] = summary
            elif rel in ["sister", "brother"]:
                pedigree["siblings"].append({"relationship": rel, **summary})
            elif rel in ["daughter", "son"]:
                pedigree["children"].append({"relationship": rel, **summary})
            elif rel in ["maternal_aunt", "maternal_uncle"]:
                pedigree["maternal"]["aunts_uncles"].append(
                    {"relationship": rel, **summary}
                )
            elif rel in ["paternal_aunt", "paternal_uncle"]:
                pedigree["paternal"]["aunts_uncles"].append(
                    {"relationship": rel, **summary}
                )

        return pedigree

    def _summarize_conditions(self, family_members: list) -> dict:
        """Summarize conditions across family"""
        conditions = {}

        for member in family_members:
            if not member.conditions:
                continue

            for cond in member.conditions:
                condition_name = cond.get("condition", "unknown")
                if condition_name not in conditions:
                    conditions[condition_name] = []

                conditions[condition_name].append(
                    {
                        "relationship": member.relationship,
                        "onset_age": cond.get("onset_age"),
                    }
                )

        return conditions

    def _summarize_risks(self, watchlist: list[WatchlistItemConfig]) -> list[dict]:
        """Summarize recommended monitoring from watchlist"""
        return [
            {
                "biomarker": item.display_name,
                "priority": item.priority,
                "threshold": f"{item.alert_direction} {item.alert_threshold} {item.unit}",
                "rationale": item.family_context,
            }
            for item in watchlist[:10]  # Top 10 priorities
        ]
