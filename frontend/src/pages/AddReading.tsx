import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Card, CardHeader, CardTitle, CardContent } from '../components/common/Card';
import {
  HeartRateForm,
  GlucoseForm,
  WeightForm,
  BloodPressureForm,
  SleepForm,
} from '../components/forms';

type ReadingType = 'heart_rate' | 'glucose' | 'weight' | 'blood_pressure' | 'sleep';

const READING_TYPES = [
  { id: 'heart_rate', name: 'Heart Rate', icon: '❤️', description: 'Resting or active heart rate' },
  { id: 'glucose', name: 'Blood Glucose', icon: '🩸', description: 'Blood sugar level' },
  { id: 'weight', name: 'Weight', icon: '⚖️', description: 'Body weight and composition' },
  { id: 'blood_pressure', name: 'Blood Pressure', icon: '💉', description: 'Systolic/diastolic pressure' },
  { id: 'sleep', name: 'Sleep', icon: '😴', description: 'Sleep session' },
] as const;

export function AddReading() {
  const [selectedType, setSelectedType] = useState<ReadingType | null>(null);
  const [successMessage, setSuccessMessage] = useState('');
  const navigate = useNavigate();

  const handleSuccess = () => {
    setSuccessMessage('Reading saved successfully!');
    setTimeout(() => {
      setSuccessMessage('');
    }, 3000);
  };

  const renderForm = () => {
    switch (selectedType) {
      case 'heart_rate':
        return <HeartRateForm onSuccess={handleSuccess} />;
      case 'glucose':
        return <GlucoseForm onSuccess={handleSuccess} />;
      case 'weight':
        return <WeightForm onSuccess={handleSuccess} />;
      case 'blood_pressure':
        return <BloodPressureForm onSuccess={handleSuccess} />;
      case 'sleep':
        return <SleepForm onSuccess={handleSuccess} />;
      default:
        return null;
    }
  };

  const selectedTypeInfo = READING_TYPES.find((t) => t.id === selectedType);

  return (
    <div className="space-y-6">
      <div className="flex justify-between items-center">
        <h1 className="text-2xl font-bold text-gray-900">Add Manual Reading</h1>
        <button
          onClick={() => navigate('/devices')}
          className="text-sm text-gray-500 hover:text-gray-700"
        >
          ← Back to Devices
        </button>
      </div>

      {successMessage && (
        <div className="bg-green-50 border border-green-200 text-green-700 px-4 py-3 rounded-lg">
          {successMessage}
        </div>
      )}

      {!selectedType ? (
        <Card>
          <CardHeader>
            <CardTitle>Select Reading Type</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
              {READING_TYPES.map((type) => (
                <button
                  key={type.id}
                  onClick={() => setSelectedType(type.id)}
                  className="p-4 border border-gray-200 rounded-lg hover:border-primary-500 hover:bg-primary-50 transition-colors text-left"
                >
                  <span className="text-2xl">{type.icon}</span>
                  <h3 className="font-medium text-gray-900 mt-2">{type.name}</h3>
                  <p className="text-sm text-gray-500">{type.description}</p>
                </button>
              ))}
            </div>
          </CardContent>
        </Card>
      ) : (
        <Card>
          <CardHeader>
            <div className="flex items-center justify-between">
              <div className="flex items-center space-x-3">
                <span className="text-2xl">{selectedTypeInfo?.icon}</span>
                <CardTitle>{selectedTypeInfo?.name}</CardTitle>
              </div>
              <button
                onClick={() => setSelectedType(null)}
                className="text-sm text-gray-500 hover:text-gray-700"
              >
                Change Type
              </button>
            </div>
          </CardHeader>
          <CardContent>
            {renderForm()}
          </CardContent>
        </Card>
      )}

      <Card>
        <CardContent>
          <h3 className="font-medium text-gray-900 mb-2">Tips for Manual Entry</h3>
          <ul className="text-sm text-gray-600 space-y-1">
            <li>• Enter readings at the time they were actually measured</li>
            <li>• For the most accurate data, use calibrated devices</li>
            <li>• Consider connecting a device for automatic tracking</li>
            <li>• Regular readings help identify trends and patterns</li>
          </ul>
        </CardContent>
      </Card>
    </div>
  );
}
