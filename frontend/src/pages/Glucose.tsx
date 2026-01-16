import { useEffect, useState } from 'react';
import { Card, CardHeader, CardTitle, CardContent } from '../components/common/Card';
import { TimeSeriesChart } from '../components/charts/TimeSeriesChart';
import { api } from '../services/api';

export function Glucose() {
  const [data, setData] = useState<Array<{ timestamp: string; value: number }>>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function loadData() {
      try {
        const end = new Date();
        const start = new Date(end.getTime() - 7 * 24 * 60 * 60 * 1000);
        const readings = await api.getGlucose(start.toISOString(), end.toISOString());
        setData(
          readings.map((r: { timestamp: string; glucose_mg_dl: number }) => ({
            timestamp: r.timestamp,
            value: r.glucose_mg_dl,
          }))
        );
      } catch (error) {
        console.error('Failed to load glucose data:', error);
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
    inRange: Math.round((data.filter(d => d.value >= 70 && d.value <= 140).length / data.length) * 100),
  } : null;

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold text-gray-900">Glucose</h1>

      {stats && (
        <div className="grid grid-cols-4 gap-4">
          <Card>
            <CardContent className="text-center py-4">
              <div className="text-3xl font-bold text-blue-500">{stats.avg}</div>
              <div className="text-sm text-gray-500">Average mg/dL</div>
            </CardContent>
          </Card>
          <Card>
            <CardContent className="text-center py-4">
              <div className="text-3xl font-bold text-green-500">{stats.min}</div>
              <div className="text-sm text-gray-500">Minimum</div>
            </CardContent>
          </Card>
          <Card>
            <CardContent className="text-center py-4">
              <div className="text-3xl font-bold text-orange-500">{stats.max}</div>
              <div className="text-sm text-gray-500">Maximum</div>
            </CardContent>
          </Card>
          <Card>
            <CardContent className="text-center py-4">
              <div className="text-3xl font-bold text-emerald-500">{stats.inRange}%</div>
              <div className="text-sm text-gray-500">Time in Range</div>
            </CardContent>
          </Card>
        </div>
      )}

      <Card>
        <CardHeader>
          <CardTitle>Glucose Over Time</CardTitle>
        </CardHeader>
        <CardContent>
          {loading ? (
            <div className="h-80 flex items-center justify-center text-gray-500">
              Loading...
            </div>
          ) : (
            <TimeSeriesChart
              data={data}
              color="#3b82f6"
              unit="mg/dL"
              referenceLines={[
                { value: 70, label: 'Low', color: '#ef4444' },
                { value: 140, label: 'High', color: '#f59e0b' },
              ]}
            />
          )}
        </CardContent>
      </Card>
    </div>
  );
}
