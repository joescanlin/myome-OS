import { useState } from 'react';
import { Button } from '../common/Button';
import { api } from '../../services/api';

interface WeightFormProps {
  onSuccess?: () => void;
}

export function WeightForm({ onSuccess }: WeightFormProps) {
  const [weight, setWeight] = useState('');
  const [unit, setUnit] = useState<'kg' | 'lbs'>('lbs');
  const [bodyFat, setBodyFat] = useState('');
  const [timestamp, setTimestamp] = useState(new Date().toISOString().slice(0, 16));
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    setLoading(true);

    let weightKg = parseFloat(weight);
    if (isNaN(weightKg) || weightKg <= 0) {
      setError('Please enter a valid weight');
      setLoading(false);
      return;
    }

    // Convert to kg if needed
    if (unit === 'lbs') {
      weightKg = weightKg * 0.453592;
    }

    if (weightKg < 20 || weightKg > 300) {
      setError('Weight must be between 20-300 kg (44-660 lbs)');
      setLoading(false);
      return;
    }

    const bodyFatPct = bodyFat ? parseFloat(bodyFat) : undefined;
    if (bodyFatPct !== undefined && (bodyFatPct < 3 || bodyFatPct > 60)) {
      setError('Body fat must be between 3% and 60%');
      setLoading(false);
      return;
    }

    try {
      await api.addBodyComposition({
        weight_kg: weightKg,
        body_fat_pct: bodyFatPct,
        timestamp: new Date(timestamp).toISOString(),
      });
      setWeight('');
      setBodyFat('');
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
          Weight
        </label>
        <div className="flex space-x-2">
          <input
            type="number"
            value={weight}
            onChange={(e) => setWeight(e.target.value)}
            placeholder={unit === 'lbs' ? '150' : '68'}
            step="0.1"
            required
            className="flex-1 px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-primary-500"
          />
          <select
            value={unit}
            onChange={(e) => setUnit(e.target.value as 'kg' | 'lbs')}
            className="px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-primary-500"
          >
            <option value="lbs">lbs</option>
            <option value="kg">kg</option>
          </select>
        </div>
      </div>

      <div>
        <label className="block text-sm font-medium text-gray-700 mb-1">
          Body Fat % (optional)
        </label>
        <input
          type="number"
          value={bodyFat}
          onChange={(e) => setBodyFat(e.target.value)}
          placeholder="20"
          min="3"
          max="60"
          step="0.1"
          className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-primary-500"
        />
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
        Save Weight
      </Button>
    </form>
  );
}
