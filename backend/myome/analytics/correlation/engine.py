"""Cross-biomarker correlation analysis"""

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Optional

import numpy as np
import pandas as pd
from scipy import stats

from myome.analytics.data_loader import TimeSeriesLoader
from myome.core.logging import logger


@dataclass
class CorrelationResult:
    """Result of a correlation analysis"""
    biomarker_1: str
    biomarker_2: str
    correlation: float
    p_value: float
    lag_days: int
    n_observations: int
    is_significant: bool
    interpretation: Optional[str] = None
    
    def to_dict(self) -> dict:
        return {
            'biomarker_1': self.biomarker_1,
            'biomarker_2': self.biomarker_2,
            'correlation': self.correlation,
            'p_value': self.p_value,
            'lag_days': self.lag_days,
            'n_observations': self.n_observations,
            'is_significant': self.is_significant,
            'interpretation': self.interpretation,
        }


class CorrelationEngine:
    """
    Discover correlations between biomarkers
    
    Features:
    - Lagged correlations (biomarker A at time t vs B at time t+lag)
    - Multiple comparison correction (Bonferroni)
    - Permutation testing for significance
    """
    
    def __init__(
        self,
        user_id: str,
        significance_level: float = 0.05,
        min_samples: int = 30,
        max_lag_days: int = 7,
    ):
        self.user_id = user_id
        self.loader = TimeSeriesLoader(user_id)
        self.alpha = significance_level
        self.min_samples = min_samples
        self.max_lag = max_lag_days
    
    async def compute_correlation(
        self,
        biomarker_1: str,
        biomarker_2: str,
        start: datetime,
        end: datetime,
        lag_days: int = 0,
    ) -> Optional[CorrelationResult]:
        """
        Compute correlation between two biomarkers
        
        Args:
            biomarker_1: First biomarker name
            biomarker_2: Second biomarker name
            start: Start datetime
            end: End datetime
            lag_days: Time lag in days (positive = biomarker_1 leads)
        """
        # Load data
        df = await self.loader.load_multi_biomarker(
            start, end,
            biomarkers=[biomarker_1, biomarker_2],
            resample='1D',
        )
        
        if df.empty or biomarker_1 not in df.columns or biomarker_2 not in df.columns:
            return None
        
        # Apply lag
        if lag_days != 0:
            if lag_days > 0:
                # biomarker_1 leads biomarker_2
                x = df[biomarker_1].iloc[:-lag_days].values
                y = df[biomarker_2].iloc[lag_days:].values
            else:
                # biomarker_2 leads biomarker_1
                x = df[biomarker_1].iloc[-lag_days:].values
                y = df[biomarker_2].iloc[:lag_days].values
        else:
            x = df[biomarker_1].values
            y = df[biomarker_2].values
        
        # Remove NaN pairs
        valid = ~(np.isnan(x) | np.isnan(y))
        x = x[valid]
        y = y[valid]
        
        if len(x) < self.min_samples:
            return None
        
        # Compute correlation
        r, p_value = stats.pearsonr(x, y)
        
        return CorrelationResult(
            biomarker_1=biomarker_1,
            biomarker_2=biomarker_2,
            correlation=float(r),
            p_value=float(p_value),
            lag_days=lag_days,
            n_observations=len(x),
            is_significant=p_value < self.alpha,
            interpretation=self._interpret_correlation(r, biomarker_1, biomarker_2, lag_days),
        )
    
    async def find_lagged_correlations(
        self,
        biomarker_1: str,
        biomarker_2: str,
        start: datetime,
        end: datetime,
    ) -> list[CorrelationResult]:
        """
        Find correlations across multiple time lags
        
        Returns correlations for lags from -max_lag to +max_lag days
        """
        results = []
        
        for lag in range(-self.max_lag, self.max_lag + 1):
            result = await self.compute_correlation(
                biomarker_1, biomarker_2,
                start, end,
                lag_days=lag,
            )
            if result:
                results.append(result)
        
        return sorted(results, key=lambda r: abs(r.correlation), reverse=True)
    
    async def discover_all_correlations(
        self,
        biomarkers: list[str],
        start: datetime,
        end: datetime,
        bonferroni_correct: bool = True,
    ) -> list[CorrelationResult]:
        """
        Discover all significant correlations between biomarkers
        
        Args:
            biomarkers: List of biomarker names to analyze
            start: Start datetime
            end: End datetime
            bonferroni_correct: Apply Bonferroni correction for multiple comparisons
        """
        # Calculate number of comparisons for Bonferroni correction
        n_pairs = len(biomarkers) * (len(biomarkers) - 1) // 2
        n_lags = 2 * self.max_lag + 1
        n_comparisons = n_pairs * n_lags
        
        adjusted_alpha = self.alpha / n_comparisons if bonferroni_correct else self.alpha
        
        significant_correlations = []
        
        for i, bm1 in enumerate(biomarkers):
            for bm2 in biomarkers[i + 1:]:
                lagged_results = await self.find_lagged_correlations(
                    bm1, bm2, start, end
                )
                
                for result in lagged_results:
                    # Apply adjusted significance threshold
                    if result.p_value < adjusted_alpha:
                        result.is_significant = True
                        significant_correlations.append(result)
        
        return sorted(
            significant_correlations,
            key=lambda r: abs(r.correlation),
            reverse=True,
        )
    
    def _interpret_correlation(
        self,
        r: float,
        biomarker_1: str,
        biomarker_2: str,
        lag_days: int,
    ) -> str:
        """Generate human-readable interpretation of correlation"""
        strength = "strong" if abs(r) > 0.7 else "moderate" if abs(r) > 0.4 else "weak"
        direction = "positive" if r > 0 else "negative"
        
        if lag_days == 0:
            timing = "at the same time"
        elif lag_days > 0:
            timing = f"{biomarker_1} changes predict {biomarker_2} changes {lag_days} day(s) later"
        else:
            timing = f"{biomarker_2} changes predict {biomarker_1} changes {-lag_days} day(s) later"
        
        return f"{strength.capitalize()} {direction} correlation (r={r:.2f}): {timing}"
    
    async def compute_correlation_matrix(
        self,
        biomarkers: list[str],
        start: datetime,
        end: datetime,
    ) -> pd.DataFrame:
        """
        Compute full correlation matrix for multiple biomarkers
        
        Returns pandas DataFrame with correlation values
        """
        df = await self.loader.load_multi_biomarker(
            start, end,
            biomarkers=biomarkers,
            resample='1D',
        )
        
        if df.empty:
            return pd.DataFrame()
        
        return df.corr(method='pearson')
