import { useEffect, useState } from 'react';
import { Card, CardHeader, CardTitle, CardContent } from '../components/common/Card';
import { TimeSeriesChart } from '../components/charts/TimeSeriesChart';
import { api } from '../services/api';

export function HeartRate() {
  const [data, setData] = useState<Array<{ timestamp: string; value: number }>>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function loadData() {
      try {
        const end = new Date();
        const start = new Date(end.getTime() - 7 * 24 * 60 * 60 * 1000);
        const readings = await api.getHeartRate(start.toISOString(), end.toISOString());
        setData(
          readings.map((r: { timestamp: string; heart_rate_bpm: number }) => ({
            timestamp: r.timestamp,
            value: r.heart_rate_bpm,
          }))
        );
      } catch (error) {
        console.error('Failed to load heart rate data:', error);
      } finally {
        setLoading(false);
      }
    }
    loadData();
  }, []);

  const stats = data.length > 0 ? {
    avg: Math.round(data.reduce((sum, d) => sum + d.value, 0) / data.length),
    min: Math.min(...data.map(d => d.value)),
    max: Math.max(...data.map(d => d.value)),
  } : null;

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold text-gray-900">Heart Rate</h1>

      {stats && (
        <div className="grid grid-cols-3 gap-4">
          <Card>
            <CardContent className="text-center py-4">
              <div className="text-3xl font-bold text-red-500">{stats.avg}</div>
              <div className="text-sm text-gray-500">Average BPM</div>
            </CardContent>
          </Card>
          <Card>
            <CardContent className="text-center py-4">
              <div className="text-3xl font-bold text-green-500">{stats.min}</div>
              <div className="text-sm text-gray-500">Resting (Min)</div>
            </CardContent>
          </Card>
          <Card>
            <CardContent className="text-center py-4">
              <div className="text-3xl font-bold text-orange-500">{stats.max}</div>
              <div className="text-sm text-gray-500">Peak (Max)</div>
            </CardContent>
          </Card>
        </div>
      )}

      <Card>
        <CardHeader>
          <CardTitle>Heart Rate Over Time</CardTitle>
        </CardHeader>
        <CardContent>
          {loading ? (
            <div className="h-80 flex items-center justify-center text-gray-500">
              Loading...
            </div>
          ) : (
            <TimeSeriesChart
              data={data}
              color="#ef4444"
              unit="BPM"
              referenceLines={[
                { value: 60, label: 'Resting', color: '#22c55e' },
                { value: 100, label: 'Elevated', color: '#f59e0b' },
              ]}
            />
          )}
        </CardContent>
      </Card>
    </div>
  );
}
