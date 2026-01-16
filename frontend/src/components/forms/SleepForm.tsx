import { useState } from 'react';
import { Button } from '../common/Button';
import { api } from '../../services/api';

interface SleepFormProps {
  onSuccess?: () => void;
}

export function SleepForm({ onSuccess }: SleepFormProps) {
  const [bedtime, setBedtime] = useState('');
  const [wakeTime, setWakeTime] = useState('');
  const [quality, setQuality] = useState<number>(3);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    setLoading(true);

    if (!bedtime || !wakeTime) {
      setError('Please enter both bedtime and wake time');
      setLoading(false);
      return;
    }

    const start = new Date(bedtime);
    const end = new Date(wakeTime);

    // Handle overnight sleep (wake time is next day)
    if (end <= start) {
      end.setDate(end.getDate() + 1);
    }

    const durationMinutes = Math.round((end.getTime() - start.getTime()) / 60000);
    
    if (durationMinutes < 30 || durationMinutes > 1440) {
      setError('Sleep duration must be between 30 minutes and 24 hours');
      setLoading(false);
      return;
    }

    try {
      await api.addSleepSession({
        start_time: start.toISOString(),
        end_time: end.toISOString(),
        total_sleep_minutes: durationMinutes,
        sleep_score: quality * 20, // Convert 1-5 to 20-100
      });
      setBedtime('');
      setWakeTime('');
      setQuality(3);
      onSuccess?.();
    } catch (err) {
      setError('Failed to save sleep session. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  // Calculate duration display
  const getDuration = () => {
    if (!bedtime || !wakeTime) return null;
    const start = new Date(bedtime);
    const end = new Date(wakeTime);
    if (end <= start) {
      end.setDate(end.getDate() + 1);
    }
    const minutes = Math.round((end.getTime() - start.getTime()) / 60000);
    const hours = Math.floor(minutes / 60);
    const mins = minutes % 60;
    return `${hours}h ${mins}m`;
  };

  const duration = getDuration();

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      <div className="grid grid-cols-2 gap-4">
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">
            Bedtime
          </label>
          <input
            type="datetime-local"
            value={bedtime}
            onChange={(e) => setBedtime(e.target.value)}
            required
            className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-primary-500"
          />
        </div>
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">
            Wake Time
          </label>
          <input
            type="datetime-local"
            value={wakeTime}
            onChange={(e) => setWakeTime(e.target.value)}
            required
            className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-primary-500"
          />
        </div>
      </div>

      {duration && (
        <p className="text-sm text-gray-600">
          Duration: <span className="font-medium">{duration}</span>
        </p>
      )}

      <div>
        <label className="block text-sm font-medium text-gray-700 mb-1">
          Sleep Quality
        </label>
        <div className="flex items-center space-x-2">
          {[1, 2, 3, 4, 5].map((value) => (
            <button
              key={value}
              type="button"
              onClick={() => setQuality(value)}
              className={`w-10 h-10 rounded-full flex items-center justify-center text-lg transition-colors ${
                quality >= value
                  ? 'bg-primary-500 text-white'
                  : 'bg-gray-100 text-gray-400 hover:bg-gray-200'
              }`}
            >
              {value <= 2 ? '😴' : value === 3 ? '😐' : '😊'}
            </button>
          ))}
        </div>
        <p className="text-xs text-gray-500 mt-1">
          {quality === 1 && 'Very Poor'}
          {quality === 2 && 'Poor'}
          {quality === 3 && 'Fair'}
          {quality === 4 && 'Good'}
          {quality === 5 && 'Excellent'}
        </p>
      </div>

      {error && (
        <p className="text-sm text-red-600">{error}</p>
      )}

      <Button type="submit" isLoading={loading} className="w-full">
        Save Sleep Session
      </Button>
    </form>
  );
}
