import { useEffect, useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { Card, CardHeader, CardTitle, CardContent } from '../components/common/Card';
import { HealthScoreGauge } from '../components/charts/HealthScoreGauge';
import { TimeSeriesChart } from '../components/charts/TimeSeriesChart';
import { DateRangePicker } from '../components/common/DateRangePicker';
import { useHealthStore } from '../store/health';
import { api } from '../services/api';
import { subDays } from 'date-fns';

interface HeartRateReading {
  timestamp: string;
  heart_rate_bpm: number;
}

interface GlucoseReading {
  timestamp: string;
  glucose_mg_dl: number;
}

interface SleepSession {
  total_sleep_minutes: number;
  deep_sleep_minutes: number;
  sleep_efficiency_pct: number | null;
}

export function Dashboard() {
  const { healthScore, alerts, fetchHealthScore, fetchAlerts, acknowledgeAlert } = useHealthStore();
  
  // Date range state - default to last 7 days
  const [dateRange, setDateRange] = useState({
    start: subDays(new Date(), 7),
    end: new Date(),
  });

  // Fetch data on mount
  useEffect(() => {
    fetchHealthScore();
    fetchAlerts();
  }, [fetchHealthScore, fetchAlerts]);

  const handleDateRangeChange = (start: Date, end: Date) => {
    setDateRange({ start, end });
  };

  // Calculate days for query key
  const daysDiff = Math.round(
    (dateRange.end.getTime() - dateRange.start.getTime()) / (1000 * 60 * 60 * 24)
  );

  // Fetch heart rate data
  const { data: heartRateData } = useQuery({
    queryKey: ['heartRate', dateRange.start.toISOString(), dateRange.end.toISOString()],
    queryFn: async () => {
      return api.getHeartRate(
        dateRange.start.toISOString(),
        dateRange.end.toISOString(),
        1000
      );
    },
  });

  // Fetch glucose data
  const { data: glucoseData } = useQuery({
    queryKey: ['glucose', dateRange.start.toISOString(), dateRange.end.toISOString()],
    queryFn: async () => {
      return api.getGlucose(
        dateRange.start.toISOString(),
        dateRange.end.toISOString(),
        1000
      );
    },
  });

  // Fetch sleep data
  const { data: sleepData } = useQuery({
    queryKey: ['sleep', dateRange.start.toISOString(), dateRange.end.toISOString()],
    queryFn: async () => {
      return api.getSleep(
        dateRange.start.toISOString(),
        dateRange.end.toISOString(),
        Math.min(daysDiff, 90)
      );
    },
  });

  return (
    <div className="space-y-6">
      {/* Header with Date Range Picker */}
      <div className="flex justify-between items-center">
        <h1 className="text-2xl font-bold text-gray-900">Dashboard</h1>
        <DateRangePicker
          startDate={dateRange.start}
          endDate={dateRange.end}
          onChange={handleDateRangeChange}
        />
      </div>

      {/* Alerts */}
      {alerts.length > 0 && (
        <Card variant="elevated" className="border-l-4 border-l-red-500">
          <CardHeader>
            <CardTitle>🚨 Active Alerts</CardTitle>
          </CardHeader>
          <CardContent>
            <ul className="space-y-3">
              {alerts.map((alert) => (
                <li
                  key={alert.id}
                  className="flex items-center justify-between p-3 bg-red-50 rounded-lg"
                >
                  <div>
                    <p className="font-medium text-red-800">{alert.title}</p>
                    <p className="text-sm text-red-600">{alert.message}</p>
                  </div>
                  <button
                    onClick={() => acknowledgeAlert(alert.id)}
                    className="text-sm text-red-600 hover:text-red-800"
                  >
                    Dismiss
                  </button>
                </li>
              ))}
            </ul>
          </CardContent>
        </Card>
      )}

      {/* Health Score & Summary */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <Card variant="elevated">
          <CardHeader>
            <CardTitle>Health Score</CardTitle>
          </CardHeader>
          <CardContent className="flex justify-center">
            <HealthScoreGauge score={healthScore?.score ?? null} />
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Score Components</CardTitle>
          </CardHeader>
          <CardContent>
            {healthScore?.components && (
              <ul className="space-y-3">
                {Object.entries(healthScore.components).map(([key, value]) => (
                  <li key={key} className="flex items-center justify-between">
                    <span className="text-gray-600 capitalize">{key.replace('_', ' ')}</span>
                    <span className="font-medium">{value.toFixed(0)}</span>
                  </li>
                ))}
              </ul>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Recent Sleep</CardTitle>
          </CardHeader>
          <CardContent>
            {sleepData?.[0] && (
              <div className="space-y-2">
                <div className="flex justify-between">
                  <span className="text-gray-600">Last Night</span>
                  <span className="font-medium">
                    {Math.round((sleepData[0] as SleepSession).total_sleep_minutes / 60)}h {(sleepData[0] as SleepSession).total_sleep_minutes % 60}m
                  </span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-600">Deep Sleep</span>
                  <span className="font-medium">{(sleepData[0] as SleepSession).deep_sleep_minutes}m</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-600">Efficiency</span>
                  <span className="font-medium">{(sleepData[0] as SleepSession).sleep_efficiency_pct?.toFixed(0)}%</span>
                </div>
              </div>
            )}
          </CardContent>
        </Card>
      </div>

      {/* Charts */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <Card>
          <CardHeader>
            <CardTitle>Heart Rate ({daysDiff} Days)</CardTitle>
          </CardHeader>
          <CardContent>
            <TimeSeriesChart
              data={(heartRateData || []).map((d: HeartRateReading) => ({
                timestamp: d.timestamp,
                value: d.heart_rate_bpm,
              }))}
              color="#E74C3C"
              unit="bpm"
            />
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Glucose ({daysDiff} Days)</CardTitle>
          </CardHeader>
          <CardContent>
            <TimeSeriesChart
              data={(glucoseData || []).map((d: GlucoseReading) => ({
                timestamp: d.timestamp,
                value: d.glucose_mg_dl,
              }))}
              color="#F39C12"
              unit="mg/dL"
              referenceLines={[
                { value: 70, label: 'Low', color: '#ef4444' },
                { value: 180, label: 'High', color: '#ef4444' },
              ]}
            />
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
