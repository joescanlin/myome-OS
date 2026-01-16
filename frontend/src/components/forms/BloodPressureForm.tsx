import { useState } from 'react';
import { Button } from '../common/Button';
import { api } from '../../services/api';

interface BloodPressureFormProps {
  onSuccess?: () => void;
}

export function BloodPressureForm({ onSuccess }: BloodPressureFormProps) {
  const [systolic, setSystolic] = useState('');
  const [diastolic, setDiastolic] = useState('');
  const [pulse, setPulse] = useState('');
  const [timestamp, setTimestamp] = useState(new Date().toISOString().slice(0, 16));
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    setLoading(true);

    const sys = parseInt(systolic);
    const dia = parseInt(diastolic);
    const pulseVal = pulse ? parseInt(pulse) : undefined;

    if (isNaN(sys) || sys < 70 || sys > 250) {
      setError('Systolic must be between 70 and 250 mmHg');
      setLoading(false);
      return;
    }

    if (isNaN(dia) || dia < 40 || dia > 150) {
      setError('Diastolic must be between 40 and 150 mmHg');
      setLoading(false);
      return;
    }

    if (sys <= dia) {
      setError('Systolic must be higher than diastolic');
      setLoading(false);
      return;
    }

    if (pulseVal !== undefined && (pulseVal < 30 || pulseVal > 200)) {
      setError('Pulse must be between 30 and 200 bpm');
      setLoading(false);
      return;
    }

    try {
      await api.addBloodPressure({
        systolic_mmhg: sys,
        diastolic_mmhg: dia,
        pulse_bpm: pulseVal,
        timestamp: new Date(timestamp).toISOString(),
      });
      setSystolic('');
      setDiastolic('');
      setPulse('');
      setTimestamp(new Date().toISOString().slice(0, 16));
      onSuccess?.();
    } catch (err) {
      setError('Failed to save reading. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  // Get BP category based on values
  const getBpCategory = () => {
    const sys = parseInt(systolic);
    const dia = parseInt(diastolic);
    if (isNaN(sys) || isNaN(dia)) return null;

    if (sys < 120 && dia < 80) return { label: 'Normal', color: 'text-green-600' };
    if (sys < 130 && dia < 80) return { label: 'Elevated', color: 'text-yellow-600' };
    if (sys < 140 || dia < 90) return { label: 'High BP Stage 1', color: 'text-orange-600' };
    if (sys >= 140 || dia >= 90) return { label: 'High BP Stage 2', color: 'text-red-600' };
    return null;
  };

  const bpCategory = getBpCategory();

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      <div className="grid grid-cols-2 gap-4">
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">
            Systolic (mmHg)
          </label>
          <input
            type="number"
            value={systolic}
            onChange={(e) => setSystolic(e.target.value)}
            placeholder="120"
            min="70"
            max="250"
            required
            className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-primary-500"
          />
        </div>
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">
            Diastolic (mmHg)
          </label>
          <input
            type="number"
            value={diastolic}
            onChange={(e) => setDiastolic(e.target.value)}
            placeholder="80"
            min="40"
            max="150"
            required
            className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-primary-500"
          />
        </div>
      </div>

      {bpCategory && (
        <p className={`text-sm font-medium ${bpCategory.color}`}>
          {bpCategory.label}
        </p>
      )}

      <div>
        <label className="block text-sm font-medium text-gray-700 mb-1">
          Pulse (bpm, optional)
        </label>
        <input
          type="number"
          value={pulse}
          onChange={(e) => setPulse(e.target.value)}
          placeholder="72"
          min="30"
          max="200"
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
        Save Blood Pressure
      </Button>
    </form>
  );
}
