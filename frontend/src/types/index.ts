// User types
export interface User {
  id: string;
  email: string;
  first_name?: string;
  last_name?: string;
  date_of_birth?: string;
  timezone: string;
  is_active: boolean;
}

// Health data types
export interface HeartRateReading {
  id: string;
  timestamp: string;
  heart_rate_bpm: number;
  activity_type?: string;
  confidence?: number;
}

export interface GlucoseReading {
  id: string;
  timestamp: string;
  glucose_mg_dl: number;
  trend?: string;
  meal_context?: string;
}

export interface SleepSession {
  id: string;
  start_time: string;
  end_time: string;
  total_sleep_minutes: number;
  deep_sleep_minutes?: number;
  rem_sleep_minutes?: number;
  light_sleep_minutes?: number;
  sleep_efficiency_pct?: number;
  sleep_score?: number;
  avg_heart_rate_bpm?: number;
  avg_hrv_ms?: number;
}

// Device types
export interface Device {
  id: string;
  name: string;
  device_type: string;
  vendor: string;
  model?: string;
  is_connected: boolean;
  last_sync_at?: string;
}

// Alert types
export interface Alert {
  id: string;
  title: string;
  message: string;
  priority: 'critical' | 'high' | 'medium' | 'low';
  status: 'active' | 'acknowledged' | 'resolved' | 'dismissed';
  biomarker: string;
  value: number;
  created_at: string;
  recommendation?: string;
}

// Analytics types
export interface HealthScore {
  score: number | null;
  components: Record<string, number>;
  weights: Record<string, number>;
}

export interface Trend {
  biomarker: string;
  start_date: string;
  end_date: string;
  slope: number;
  direction: 'increasing' | 'decreasing' | 'stable';
  percent_change: number;
  is_significant: boolean;
}

export interface Correlation {
  biomarker_1: string;
  biomarker_2: string;
  correlation: number;
  p_value: number;
  lag_days: number;
  n_observations: number;
  is_significant: boolean;
  interpretation?: string;
}

// API response types
export interface TokenPair {
  access_token: string;
  refresh_token: string;
  token_type: string;
}

export interface DailyAnalysis {
  date: string;
  alerts: Alert[];
  trends: Trend[];
  correlations: Correlation[];
  daily_summary: {
    heart_rate?: {
      mean: number;
      min: number;
      max: number;
    };
    glucose?: {
      mean: number;
      min: number;
      max: number;
      time_in_range_pct: number;
    };
    hrv?: {
      sdnn_mean: number | null;
      rmssd_mean: number | null;
    };
    sleep?: {
      total_minutes: number;
      deep_minutes: number;
      efficiency_pct: number;
    };
  };
}
