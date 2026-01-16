"""Trend detection and change-point analysis"""

from dataclasses import dataclass
from datetime import datetime
from typing import Optional

import numpy as np
import pandas as pd
from scipy import stats


@dataclass
class TrendResult:
    """Result of trend analysis"""
    biomarker: str
    start_date: datetime
    end_date: datetime
    slope: float
    slope_per_day: float
    r_squared: float
    p_value: float
    direction: str  # 'increasing', 'decreasing', 'stable'
    is_significant: bool
    percent_change: float
    
    def to_dict(self) -> dict:
        return {
            'biomarker': self.biomarker,
            'start_date': self.start_date.isoformat(),
            'end_date': self.end_date.isoformat(),
            'slope': self.slope,
            'slope_per_day': self.slope_per_day,
            'r_squared': self.r_squared,
            'p_value': self.p_value,
            'direction': self.direction,
            'is_significant': self.is_significant,
            'percent_change': self.percent_change,
        }


@dataclass
class ChangePoint:
    """Detected change point in time series"""
    timestamp: datetime
    before_mean: float
    after_mean: float
    change_magnitude: float
    change_percent: float
    confidence: float


class TrendAnalyzer:
    """Analyze trends and detect change points in biomarker time series"""
    
    def __init__(self, significance_level: float = 0.05):
        self.alpha = significance_level
    
    def compute_trend(
        self,
        data: pd.Series,
        biomarker_name: str,
    ) -> Optional[TrendResult]:
        """
        Compute linear trend in time series
        
        Args:
            data: pandas Series with datetime index
            biomarker_name: Name of biomarker for reporting
        """
        if len(data) < 7:  # Need at least a week of data
            return None
        
        # Remove NaN
        data = data.dropna()
        if len(data) < 7:
            return None
        
        # Convert to numeric days from start
        start_date = data.index.min()
        end_date = data.index.max()
        
        x = np.array([(t - start_date).days for t in data.index])
        y = data.values
        
        # Linear regression
        slope, intercept, r_value, p_value, std_err = stats.linregress(x, y)
        
        # Calculate percent change
        start_value = intercept
        end_value = intercept + slope * x[-1]
        if start_value != 0:
            percent_change = ((end_value - start_value) / abs(start_value)) * 100
        else:
            percent_change = 0
        
        # Determine direction
        if p_value < self.alpha:
            direction = 'increasing' if slope > 0 else 'decreasing'
        else:
            direction = 'stable'
        
        return TrendResult(
            biomarker=biomarker_name,
            start_date=start_date,
            end_date=end_date,
            slope=float(slope),
            slope_per_day=float(slope),
            r_squared=float(r_value ** 2),
            p_value=float(p_value),
            direction=direction,
            is_significant=p_value < self.alpha,
            percent_change=float(percent_change),
        )
    
    def detect_change_points(
        self,
        data: pd.Series,
        min_segment_size: int = 7,
        threshold_std: float = 2.0,
    ) -> list[ChangePoint]:
        """
        Detect change points using simple segmentation
        
        Uses a sliding window approach to find significant level shifts
        """
        if len(data) < min_segment_size * 2:
            return []
        
        data = data.dropna()
        if len(data) < min_segment_size * 2:
            return []
        
        change_points = []
        values = data.values
        timestamps = data.index
        
        # Calculate global statistics for threshold
        global_std = np.std(values)
        
        # Sliding window comparison
        for i in range(min_segment_size, len(values) - min_segment_size):
            before = values[i - min_segment_size:i]
            after = values[i:i + min_segment_size]
            
            before_mean = np.mean(before)
            after_mean = np.mean(after)
            
            change = after_mean - before_mean
            
            # Check if change exceeds threshold
            if abs(change) > threshold_std * global_std:
                # Compute confidence based on t-test
                t_stat, p_value = stats.ttest_ind(before, after)
                confidence = 1 - p_value
                
                if confidence > 0.95:  # 95% confidence
                    percent_change = (change / abs(before_mean)) * 100 if before_mean != 0 else 0
                    
                    change_points.append(ChangePoint(
                        timestamp=timestamps[i],
                        before_mean=float(before_mean),
                        after_mean=float(after_mean),
                        change_magnitude=float(change),
                        change_percent=float(percent_change),
                        confidence=float(confidence),
                    ))
        
        # Merge nearby change points (within 3 days)
        merged = self._merge_nearby_changepoints(change_points)
        
        return merged
    
    def _merge_nearby_changepoints(
        self,
        change_points: list[ChangePoint],
        max_gap_days: int = 3,
    ) -> list[ChangePoint]:
        """Merge change points that are close together"""
        if not change_points:
            return []
        
        # Sort by timestamp
        sorted_cps = sorted(change_points, key=lambda cp: cp.timestamp)
        
        merged = [sorted_cps[0]]
        
        for cp in sorted_cps[1:]:
            last = merged[-1]
            gap = (cp.timestamp - last.timestamp).days
            
            if gap <= max_gap_days:
                # Keep the one with higher confidence
                if cp.confidence > last.confidence:
                    merged[-1] = cp
            else:
                merged.append(cp)
        
        return merged
