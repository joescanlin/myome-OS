import { useState } from 'react';
import { Button } from '../common/Button';
import { api } from '../../services/api';

interface HeartRateFormProps {
  onSuccess?: () => void;
}

export function HeartRateForm({ onSuccess }: HeartRateFormProps) {
  const [heartRate, setHeartRate] = useState('');
  const [activityType, setActivityType] = useState('resting');
  const [timestamp, setTimestamp] = useState(new Date().toISOString().slice(0, 16));
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    setLoading(true);

    const hr = parseInt(heartRate);
    if (isNaN(hr) || hr < 30 || hr > 250) {
      setError('Heart rate must be between 30 and 250 bpm');
      setLoading(false);
      return;
    }

    try {
      await api.addHeartRateReading({
        heart_rate_bpm: hr,
        activity_type: activityType,
        timestamp: new Date(timestamp).toISOString(),
      });
      setHeartRate('');
      setActivityType('resting');
      setTimestamp(new Date().toISOString().slice(0, 16));
      onSuccess?.();
    } catch (err) {
      setError('Failed to save reading. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      <div>
        <label className="block text-sm font-medium text-gray-700 mb-1">
          Heart Rate (bpm)
        </label>
        <input
          type="number"
          value={heartRate}
          onChange={(e) => setHeartRate(e.target.value)}
          placeholder="72"
          min="30"
          max="250"
          required
          className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-primary-500"
        />
      </div>

      <div>
        <label className="block text-sm font-medium text-gray-700 mb-1">
          Activity Type
        </label>
        <select
          value={activityType}
          onChange={(e) => setActivityType(e.target.value)}
          className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-primary-500"
        >
          <option value="resting">Resting</option>
          <option value="walking">Walking</option>
          <option value="exercise">Exercise</option>
          <option value="sleeping">Sleeping</option>
          <option value="other">Other</option>
        </select>
      </div>

      <div>
        <label className="block text-sm font-medium text-gray-700 mb-1">
          Date & Time
        </label>
        <input
          type="datetime-local"
          value={timestamp}
          onChange={(e) => setTimestamp(e.target.value)}
          className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-primary-500"
        />
      </div>

      {error && (
        <p className="text-sm text-red-600">{error}</p>
      )}

      <Button type="submit" isLoading={loading} className="w-full">
        Save Heart Rate
      </Button>
    </form>
  );
}
