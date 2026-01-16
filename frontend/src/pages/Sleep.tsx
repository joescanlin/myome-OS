import { useEffect, useState } from 'react';
import { Card, CardHeader, CardTitle, CardContent } from '../components/common/Card';
import { api } from '../services/api';

interface SleepSession {
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

export function Sleep() {
  const [sessions, setSessions] = useState<SleepSession[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function loadData() {
      try {
        const end = new Date();
        const start = new Date(end.getTime() - 14 * 24 * 60 * 60 * 1000);
        const data = await api.getSleep(start.toISOString(), end.toISOString());
        setSessions(data);
      } catch (error) {
        console.error('Failed to load sleep data:', error);
      } finally {
        setLoading(false);
      }
    }
    loadData();
  }, []);

  const formatDuration = (minutes: number) => {
    const hours = Math.floor(minutes / 60);
    const mins = minutes % 60;
    return `${hours}h ${mins}m`;
  };

  const avgSleep = sessions.length > 0
    ? Math.round(sessions.reduce((sum, s) => sum + s.total_sleep_minutes, 0) / sessions.length)
    : 0;

  const avgScore = sessions.length > 0
    ? Math.round(sessions.reduce((sum, s) => sum + (s.sleep_score || 0), 0) / sessions.length)
    : 0;

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-gray-500">Loading sleep data...</div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold text-gray-900">Sleep</h1>

      <div className="grid grid-cols-3 gap-4">
        <Card>
          <CardContent className="text-center py-4">
            <div className="text-3xl font-bold text-indigo-500">{formatDuration(avgSleep)}</div>
            <div className="text-sm text-gray-500">Avg Sleep Duration</div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="text-center py-4">
            <div className="text-3xl font-bold text-purple-500">{avgScore}</div>
            <div className="text-sm text-gray-500">Avg Sleep Score</div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="text-center py-4">
            <div className="text-3xl font-bold text-blue-500">{sessions.length}</div>
            <div className="text-sm text-gray-500">Nights Tracked</div>
          </CardContent>
        </Card>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Sleep History</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-4">
            {sessions.map((session) => (
              <div
                key={session.id}
                className="flex items-center justify-between p-4 bg-gray-50 rounded-lg"
              >
                <div>
                  <div className="font-medium">
                    {new Date(session.start_time).toLocaleDateString('en-US', {
                      weekday: 'short',
                      month: 'short',
                      day: 'numeric',
                    })}
                  </div>
                  <div className="text-sm text-gray-500">
                    {new Date(session.start_time).toLocaleTimeString('en-US', {
                      hour: 'numeric',
                      minute: '2-digit',
                    })}
                    {' - '}
                    {new Date(session.end_time).toLocaleTimeString('en-US', {
                      hour: 'numeric',
                      minute: '2-digit',
                    })}
                  </div>
                </div>
                <div className="text-right">
                  <div className="text-lg font-semibold">
                    {formatDuration(session.total_sleep_minutes)}
                  </div>
                  {session.sleep_score && (
                    <div className="text-sm text-gray-500">
                      Score: {session.sleep_score}
                    </div>
                  )}
                </div>
                <div className="flex space-x-4 text-sm">
                  {session.deep_sleep_minutes && (
                    <div className="text-center">
                      <div className="font-medium text-indigo-600">
                        {formatDuration(session.deep_sleep_minutes)}
                      </div>
                      <div className="text-gray-400">Deep</div>
                    </div>
                  )}
                  {session.rem_sleep_minutes && (
                    <div className="text-center">
                      <div className="font-medium text-purple-600">
                        {formatDuration(session.rem_sleep_minutes)}
                      </div>
                      <div className="text-gray-400">REM</div>
                    </div>
                  )}
                  {session.light_sleep_minutes && (
                    <div className="text-center">
                      <div className="font-medium text-blue-600">
                        {formatDuration(session.light_sleep_minutes)}
                      </div>
                      <div className="text-gray-400">Light</div>
                    </div>
                  )}
                </div>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
