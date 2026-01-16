"""Family-calibrated risk calculation"""

from dataclasses import dataclass, field
from typing import Optional
import numpy as np


@dataclass
class FamilyOutcome:
    """Health outcome from a family member"""
    condition: str
    onset_age: Optional[int]
    relatedness: float  # 0.5 for parent, 0.25 for grandparent
    genetic_similarity: float = 1.0  # 0-1 based on shared variants
    relationship: str = "unknown"


@dataclass
class FamilyCalibratedRisk:
    """Result of family-calibrated risk calculation"""
    condition: str
    population_risk: float
    family_calibrated_risk: float
    confidence_interval: tuple[float, float]
    risk_increase_factor: float
    contributing_factors: list[str]
    recommendation: Optional[str] = None


# Standard population risk estimates for common conditions
POPULATION_RISKS = {
    "type_2_diabetes": 0.10,  # ~10% lifetime risk
    "coronary_artery_disease": 0.15,  # ~15% lifetime risk
    "hypertension": 0.30,  # ~30% lifetime risk
    "stroke": 0.08,  # ~8% lifetime risk
    "breast_cancer": 0.12,  # ~12% for women
    "colon_cancer": 0.04,  # ~4% lifetime risk
    "alzheimers": 0.10,  # ~10% over 65
    "atrial_fibrillation": 0.25,  # ~25% over 40
}

# Age adjustment factors (earlier onset = higher genetic component)
EARLY_ONSET_THRESHOLDS = {
    "type_2_diabetes": 45,
    "coronary_artery_disease": 55,
    "hypertension": 40,
    "stroke": 55,
    "breast_cancer": 50,
    "colon_cancer": 50,
    "alzheimers": 65,
    "atrial_fibrillation": 60,
}


class FamilyRiskCalculator:
    """
    Calculate family-calibrated disease risk
    
    Uses Bayesian updating to refine population-based risk scores
    with family health outcomes.
    """
    
    def __init__(self, condition: str):
        self.condition = condition
        self.population_risk = POPULATION_RISKS.get(condition, 0.05)
        self.early_onset_threshold = EARLY_ONSET_THRESHOLDS.get(condition, 55)
    
    def calculate_risk(
        self,
        family_outcomes: list[FamilyOutcome],
        user_age: int,
        polygenic_risk_score: Optional[float] = None,
    ) -> FamilyCalibratedRisk:
        """
        Calculate family-calibrated risk
        
        Args:
            family_outcomes: Health outcomes from family members
            user_age: Current age of the user
            polygenic_risk_score: Optional PRS percentile (0-1)
        """
        # Start with population or PRS-adjusted risk
        if polygenic_risk_score is not None:
            # PRS adjusts population risk
            base_risk = self._prs_adjusted_risk(polygenic_risk_score)
        else:
            base_risk = self.population_risk
        
        # Filter to relevant condition
        relevant_outcomes = [
            o for o in family_outcomes
            if o.condition.lower() == self.condition.lower()
        ]
        
        if not relevant_outcomes:
            return FamilyCalibratedRisk(
                condition=self.condition,
                population_risk=self.population_risk,
                family_calibrated_risk=base_risk,
                confidence_interval=(base_risk * 0.5, min(base_risk * 2, 1.0)),
                risk_increase_factor=1.0,
                contributing_factors=["No family history data available"],
                recommendation=self._generate_recommendation(base_risk, []),
            )
        
        # Calculate family likelihood ratio
        likelihood_ratio = self._compute_family_likelihood(relevant_outcomes, user_age)
        
        # Bayesian update
        posterior = self._bayesian_update(base_risk, likelihood_ratio)
        
        # Identify contributing factors
        factors = self._identify_factors(relevant_outcomes)
        
        # Calculate risk increase
        risk_factor = posterior['mean'] / self.population_risk if self.population_risk > 0 else 1.0
        
        return FamilyCalibratedRisk(
            condition=self.condition,
            population_risk=self.population_risk,
            family_calibrated_risk=posterior['mean'],
            confidence_interval=(posterior['ci_low'], posterior['ci_high']),
            risk_increase_factor=risk_factor,
            contributing_factors=factors,
            recommendation=self._generate_recommendation(posterior['mean'], relevant_outcomes),
        )
    
    def _prs_adjusted_risk(self, prs_percentile: float) -> float:
        """Adjust population risk based on PRS percentile"""
        # Simplified model: PRS at 50th percentile = population risk
        # Top 1% = ~3x risk, bottom 1% = ~0.3x risk
        if prs_percentile >= 0.99:
            multiplier = 3.0
        elif prs_percentile >= 0.95:
            multiplier = 2.0
        elif prs_percentile >= 0.80:
            multiplier = 1.5
        elif prs_percentile <= 0.01:
            multiplier = 0.3
        elif prs_percentile <= 0.05:
            multiplier = 0.5
        elif prs_percentile <= 0.20:
            multiplier = 0.7
        else:
            multiplier = 1.0
        
        return min(self.population_risk * multiplier, 0.95)
    
    def _compute_family_likelihood(
        self,
        outcomes: list[FamilyOutcome],
        user_age: int,
    ) -> float:
        """Compute likelihood ratio from family outcomes"""
        weighted_affected = 0.0
        total_weight = 0.0
        
        for outcome in outcomes:
            # Weight by genetic relatedness
            weight = outcome.relatedness * outcome.genetic_similarity
            total_weight += weight
            
            if outcome.onset_age is not None:
                # Earlier onset = stronger signal
                age_factor = self._age_adjustment(outcome.onset_age)
                weighted_affected += weight * age_factor
            else:
                # Affected but unknown onset
                weighted_affected += weight * 0.8
        
        if total_weight == 0:
            return 1.0
        
        # Normalize and compute likelihood ratio
        affected_proportion = weighted_affected / total_weight
        
        # More affected relatives = higher likelihood ratio
        # Sigmoid function to bound between 0.5 and 4.0
        likelihood_ratio = 0.5 + 3.5 / (1 + np.exp(-3 * (affected_proportion - 0.5)))
        
        return likelihood_ratio
    
    def _age_adjustment(self, onset_age: int) -> float:
        """
        Adjust weight based on age of onset
        
        Earlier onset suggests stronger genetic component
        """
        threshold = self.early_onset_threshold
        
        if onset_age < threshold - 10:
            return 2.0  # Very early onset
        elif onset_age < threshold:
            return 1.5  # Early onset
        elif onset_age < threshold + 10:
            return 1.0  # Typical onset
        else:
            return 0.7  # Late onset
    
    def _bayesian_update(
        self,
        prior: float,
        likelihood_ratio: float,
    ) -> dict:
        """Perform Bayesian update on risk probability"""
        # Convert to odds
        prior = max(0.001, min(0.999, prior))  # Bound away from 0 and 1
        prior_odds = prior / (1 - prior)
        
        # Update with likelihood ratio
        posterior_odds = prior_odds * likelihood_ratio
        posterior_prob = posterior_odds / (1 + posterior_odds)
        
        # Estimate confidence interval based on data quality
        ci_width = 0.15 / max(likelihood_ratio, 0.5)
        ci_low = max(0.001, posterior_prob - ci_width)
        ci_high = min(0.999, posterior_prob + ci_width)
        
        return {
            'mean': posterior_prob,
            'ci_low': ci_low,
            'ci_high': ci_high,
        }
    
    def _identify_factors(self, outcomes: list[FamilyOutcome]) -> list[str]:
        """Identify key contributing factors"""
        factors = []
        
        # Check for early onset
        early_onset = [o for o in outcomes if o.onset_age and o.onset_age < self.early_onset_threshold]
        if early_onset:
            ages = [o.onset_age for o in early_onset]
            factors.append(f"Early onset in family (age {min(ages)}-{max(ages)})")
        
        # Check for first-degree relatives
        first_degree = [o for o in outcomes if o.relatedness >= 0.5]
        if first_degree:
            relationships = list(set(o.relationship for o in first_degree))
            factors.append(f"First-degree relative(s) affected: {', '.join(relationships)}")
        
        # Check for multiple affected
        if len(outcomes) > 1:
            factors.append(f"{len(outcomes)} family members affected")
        
        return factors if factors else ["Family history present"]
    
    def _generate_recommendation(
        self,
        risk: float,
        outcomes: list[FamilyOutcome],
    ) -> str:
        """Generate clinical recommendation based on risk level"""
        has_early_onset = any(
            o.onset_age and o.onset_age < self.early_onset_threshold
            for o in outcomes
        )
        
        if risk >= 0.30:
            return f"High risk for {self.condition}. Recommend specialist consultation and enhanced screening."
        elif risk >= 0.15:
            if has_early_onset:
                return f"Elevated risk with early-onset family history. Consider earlier screening initiation."
            return f"Moderately elevated risk. Follow standard screening guidelines closely."
        elif risk >= 0.05:
            return f"Average to slightly elevated risk. Maintain healthy lifestyle and regular check-ups."
        else:
            return f"Below average risk. Continue standard preventive care."


class ComprehensiveRiskAssessment:
    """
    Generate comprehensive risk assessment across multiple conditions
    """
    
    CONDITIONS = list(POPULATION_RISKS.keys())
    
    def __init__(self, user_age: int):
        self.user_age = user_age
        self.calculators = {
            condition: FamilyRiskCalculator(condition)
            for condition in self.CONDITIONS
        }
    
    def assess_all_risks(
        self,
        family_outcomes: list[FamilyOutcome],
        polygenic_scores: Optional[dict[str, float]] = None,
    ) -> dict[str, FamilyCalibratedRisk]:
        """
        Calculate risk for all tracked conditions
        
        Args:
            family_outcomes: All family health outcomes
            polygenic_scores: Dict mapping condition to PRS percentile
        """
        results = {}
        
        for condition, calculator in self.calculators.items():
            prs = polygenic_scores.get(condition) if polygenic_scores else None
            results[condition] = calculator.calculate_risk(
                family_outcomes=family_outcomes,
                user_age=self.user_age,
                polygenic_risk_score=prs,
            )
        
        return results
    
    def get_priority_conditions(
        self,
        risks: dict[str, FamilyCalibratedRisk],
        threshold: float = 1.5,
    ) -> list[FamilyCalibratedRisk]:
        """
        Get conditions where family-calibrated risk exceeds threshold
        
        Args:
            risks: Results from assess_all_risks
            threshold: Risk increase factor threshold
        """
        priority = [
            risk for risk in risks.values()
            if risk.risk_increase_factor >= threshold
        ]
        return sorted(priority, key=lambda r: r.risk_increase_factor, reverse=True)
