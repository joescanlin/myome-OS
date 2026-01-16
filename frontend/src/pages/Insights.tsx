import { useEffect, useState } from 'react';
import { Card, CardHeader, CardTitle, CardContent } from '../components/common/Card';
import { api } from '../services/api';

interface Correlation {
  biomarker_a: string;
  biomarker_b: string;
  coefficient: number;
  p_value: number;
  strength: string;
}

interface Trend {
  biomarker: string;
  direction: string;
  slope: number;
  description: string;
}

export function Insights() {
  const [correlations, setCorrelations] = useState<Correlation[]>([]);
  const [trends, setTrends] = useState<Trend[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function loadData() {
      try {
        const [corrData, trendData] = await Promise.all([
          api.getCorrelations(30),
          api.getTrends(30),
        ]);
        setCorrelations(corrData);
        setTrends(trendData);
      } catch (error) {
        console.error('Failed to load insights:', error);
      } finally {
        setLoading(false);
      }
    }
    loadData();
  }, []);

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-gray-500">Analyzing your health data...</div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold text-gray-900">Health Insights</h1>

      <Card>
        <CardHeader>
          <CardTitle>Biomarker Correlations</CardTitle>
        </CardHeader>
        <CardContent>
          {correlations.length > 0 ? (
            <div className="space-y-4">
              {correlations.map((corr, i) => (
                <div
                  key={i}
                  className="flex items-center justify-between p-4 bg-gray-50 rounded-lg"
                >
                  <div>
                    <span className="font-medium capitalize">
                      {corr.biomarker_a.replace('_', ' ')}
                    </span>
                    <span className="mx-2 text-gray-400">↔</span>
                    <span className="font-medium capitalize">
                      {corr.biomarker_b.replace('_', ' ')}
                    </span>
                  </div>
                  <div className="text-right">
                    <div
                      className={`font-semibold ${
                        corr.coefficient > 0 ? 'text-green-600' : 'text-red-600'
                      }`}
                    >
                      {corr.coefficient > 0 ? '+' : ''}
                      {(corr.coefficient * 100).toFixed(0)}%
                    </div>
                    <div className="text-sm text-gray-500 capitalize">
                      {corr.strength} correlation
                    </div>
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <p className="text-gray-500 text-center py-8">
              Not enough data yet to find correlations. Keep tracking!
            </p>
          )}
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Trends</CardTitle>
        </CardHeader>
        <CardContent>
          {trends.length > 0 ? (
            <div className="space-y-4">
              {trends.map((trend, i) => (
                <div
                  key={i}
                  className="flex items-center justify-between p-4 bg-gray-50 rounded-lg"
                >
                  <div>
                    <span className="font-medium capitalize">
                      {trend.biomarker.replace('_', ' ')}
                    </span>
                    <p className="text-sm text-gray-500 mt-1">
                      {trend.description}
                    </p>
                  </div>
                  <div
                    className={`text-2xl ${
                      trend.direction === 'increasing' ? 'text-green-500' : 'text-red-500'
                    }`}
                  >
                    {trend.direction === 'increasing' ? '↑' : '↓'}
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <p className="text-gray-500 text-center py-8">
              No significant trends detected yet. Keep tracking!
            </p>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
