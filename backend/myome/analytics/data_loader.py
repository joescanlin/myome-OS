"""Data loading utilities for analytics"""

from datetime import datetime, timedelta
from typing import Optional

import numpy as np
import pandas as pd
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from myome.core.database import get_session_context
from myome.core.models import (
    GlucoseReading,
    HeartRateReading,
    HRVReading,
    SleepSession,
    ActivityReading,
    BodyComposition,
    BiomarkerReading,
)


class TimeSeriesLoader:
    """Load and prepare time-series data for analysis"""
    
    def __init__(self, user_id: str):
        self.user_id = user_id
    
    async def load_heart_rate(
        self,
        start: datetime,
        end: datetime,
        resample: Optional[str] = None,
    ) -> pd.DataFrame:
        """
        Load heart rate data as pandas DataFrame
        
        Args:
            start: Start datetime
            end: End datetime
            resample: Optional resampling frequency (e.g., '1H', '1D')
        """
        async with get_session_context() as session:
            query = select(HeartRateReading).where(
                HeartRateReading.user_id == self.user_id,
                HeartRateReading.timestamp >= start,
                HeartRateReading.timestamp <= end,
            ).order_by(HeartRateReading.timestamp)
            
            result = await session.execute(query)
            readings = result.scalars().all()
        
        if not readings:
            return pd.DataFrame(columns=['timestamp', 'heart_rate_bpm'])
        
        df = pd.DataFrame([
            {
                'timestamp': r.timestamp,
                'heart_rate_bpm': r.heart_rate_bpm,
                'confidence': r.confidence,
            }
            for r in readings
        ])
        
        df.set_index('timestamp', inplace=True)
        
        if resample:
            df = df.resample(resample).agg({
                'heart_rate_bpm': 'mean',
                'confidence': 'mean',
            })
        
        return df
    
    async def load_glucose(
        self,
        start: datetime,
        end: datetime,
        resample: Optional[str] = None,
    ) -> pd.DataFrame:
        """Load glucose data as pandas DataFrame"""
        async with get_session_context() as session:
            query = select(GlucoseReading).where(
                GlucoseReading.user_id == self.user_id,
                GlucoseReading.timestamp >= start,
                GlucoseReading.timestamp <= end,
            ).order_by(GlucoseReading.timestamp)
            
            result = await session.execute(query)
            readings = result.scalars().all()
        
        if not readings:
            return pd.DataFrame(columns=['timestamp', 'glucose_mg_dl'])
        
        df = pd.DataFrame([
            {
                'timestamp': r.timestamp,
                'glucose_mg_dl': r.glucose_mg_dl,
                'trend': r.trend,
            }
            for r in readings
        ])
        
        df.set_index('timestamp', inplace=True)
        
        if resample:
            df = df.resample(resample).agg({
                'glucose_mg_dl': 'mean',
            })
        
        return df
    
    async def load_hrv(
        self,
        start: datetime,
        end: datetime,
        resample: Optional[str] = None,
    ) -> pd.DataFrame:
        """Load HRV data as pandas DataFrame"""
        async with get_session_context() as session:
            query = select(HRVReading).where(
                HRVReading.user_id == self.user_id,
                HRVReading.timestamp >= start,
                HRVReading.timestamp <= end,
            ).order_by(HRVReading.timestamp)
            
            result = await session.execute(query)
            readings = result.scalars().all()
        
        if not readings:
            return pd.DataFrame(columns=['timestamp', 'sdnn_ms', 'rmssd_ms'])
        
        df = pd.DataFrame([
            {
                'timestamp': r.timestamp,
                'sdnn_ms': r.sdnn_ms,
                'rmssd_ms': r.rmssd_ms,
                'pnn50_pct': r.pnn50_pct,
                'lf_hf_ratio': r.lf_hf_ratio,
            }
            for r in readings
        ])
        
        df.set_index('timestamp', inplace=True)
        
        if resample:
            df = df.resample(resample).mean()
        
        return df
    
    async def load_sleep(
        self,
        start: datetime,
        end: datetime,
    ) -> pd.DataFrame:
        """Load sleep session data"""
        async with get_session_context() as session:
            query = select(SleepSession).where(
                SleepSession.user_id == self.user_id,
                SleepSession.start_time >= start,
                SleepSession.start_time <= end,
            ).order_by(SleepSession.start_time)
            
            result = await session.execute(query)
            sessions = result.scalars().all()
        
        if not sessions:
            return pd.DataFrame()
        
        df = pd.DataFrame([
            {
                'date': s.start_time.date(),
                'total_sleep_minutes': s.total_sleep_minutes,
                'deep_sleep_minutes': s.deep_sleep_minutes,
                'rem_sleep_minutes': s.rem_sleep_minutes,
                'light_sleep_minutes': s.light_sleep_minutes,
                'sleep_efficiency_pct': s.sleep_efficiency_pct,
                'sleep_onset_latency': s.sleep_onset_latency_minutes,
                'avg_heart_rate': s.avg_heart_rate_bpm,
                'avg_hrv': s.avg_hrv_ms,
            }
            for s in sessions
        ])
        
        df.set_index('date', inplace=True)
        return df
    
    async def load_multi_biomarker(
        self,
        start: datetime,
        end: datetime,
        biomarkers: list[str],
        resample: str = '1D',
    ) -> pd.DataFrame:
        """
        Load multiple biomarker time-series aligned for correlation analysis
        
        Returns DataFrame with columns for each biomarker
        """
        # Load each data type
        hr_df = await self.load_heart_rate(start, end, resample)
        glucose_df = await self.load_glucose(start, end, resample)
        hrv_df = await self.load_hrv(start, end, resample)
        sleep_df = await self.load_sleep(start, end)
        
        # Combine into single DataFrame
        dfs = []
        
        if 'heart_rate' in biomarkers and not hr_df.empty:
            dfs.append(hr_df[['heart_rate_bpm']].rename(columns={'heart_rate_bpm': 'heart_rate'}))
        
        if 'glucose' in biomarkers and not glucose_df.empty:
            dfs.append(glucose_df[['glucose_mg_dl']].rename(columns={'glucose_mg_dl': 'glucose'}))
        
        if 'hrv_sdnn' in biomarkers and not hrv_df.empty:
            if 'sdnn_ms' in hrv_df.columns:
                dfs.append(hrv_df[['sdnn_ms']].rename(columns={'sdnn_ms': 'hrv_sdnn'}))
        
        if 'hrv_rmssd' in biomarkers and not hrv_df.empty:
            if 'rmssd_ms' in hrv_df.columns:
                dfs.append(hrv_df[['rmssd_ms']].rename(columns={'rmssd_ms': 'hrv_rmssd'}))
        
        if not dfs:
            return pd.DataFrame()
        
        # Merge all DataFrames on timestamp index
        combined = dfs[0]
        for df in dfs[1:]:
            combined = combined.join(df, how='outer')
        
        # Handle sleep data (daily, needs special treatment)
        if any(b.startswith('sleep_') for b in biomarkers) and not sleep_df.empty:
            sleep_df.index = pd.to_datetime(sleep_df.index)
            combined = combined.join(sleep_df, how='outer')
        
        return combined
