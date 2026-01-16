import { useState } from 'react';
import { Button } from '../common/Button';
import { api } from '../../services/api';

interface GlucoseFormProps {
  onSuccess?: () => void;
}

export function GlucoseForm({ onSuccess }: GlucoseFormProps) {
  const [glucose, setGlucose] = useState('');
  const [mealContext, setMealContext] = useState('fasting');
  const [timestamp, setTimestamp] = useState(new Date().toISOString().slice(0, 16));
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    setLoading(true);

    const glucoseValue = parseFloat(glucose);
    if (isNaN(glucoseValue) || glucoseValue < 20 || glucoseValue > 600) {
      setError('Glucose must be between 20 and 600 mg/dL');
      setLoading(false);
      return;
    }

    try {
      await api.addGlucoseReading({
        glucose_mg_dl: glucoseValue,
        meal_context: mealContext,
        timestamp: new Date(timestamp).toISOString(),
      });
      setGlucose('');
      setMealContext('fasting');
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
          Blood Glucose (mg/dL)
        </label>
        <input
          type="number"
          value={glucose}
          onChange={(e) => setGlucose(e.target.value)}
          placeholder="100"
          min="20"
          max="600"
          step="0.1"
          required
          className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-primary-500"
        />
      </div>

      <div>
        <label className="block text-sm font-medium text-gray-700 mb-1">
          Meal Context
        </label>
        <select
          value={mealContext}
          onChange={(e) => setMealContext(e.target.value)}
          className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-primary-500"
        >
          <option value="fasting">Fasting (8+ hours)</option>
          <option value="before_meal">Before Meal</option>
          <option value="after_meal">After Meal (2 hours)</option>
          <option value="bedtime">Bedtime</option>
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
        Save Glucose Reading
      </Button>
    </form>
  );
}
