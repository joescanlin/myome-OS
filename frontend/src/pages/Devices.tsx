import { useEffect, useState } from 'react';
import { Card, CardHeader, CardTitle, CardContent } from '../components/common/Card';
import { Button } from '../components/common/Button';
import { api } from '../services/api';

interface Device {
  id: string;
  name: string;
  device_type: string;
  vendor: string;
  model?: string;
  is_connected: boolean;
  last_sync_at?: string;
}

export function Devices() {
  const [devices, setDevices] = useState<Device[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function loadDevices() {
      try {
        const data = await api.getDevices();
        setDevices(data);
      } catch (error) {
        console.error('Failed to load devices:', error);
      } finally {
        setLoading(false);
      }
    }
    loadDevices();
  }, []);

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-gray-500">Loading devices...</div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex justify-between items-center">
        <h1 className="text-2xl font-bold text-gray-900">Connected Devices</h1>
        <Button variant="primary">Add Device</Button>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        {devices.map((device) => (
          <Card key={device.id}>
            <CardHeader>
              <CardTitle>{device.name}</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-2">
                <div className="flex justify-between">
                  <span className="text-gray-500">Type</span>
                  <span className="capitalize">{device.device_type.replace('_', ' ')}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-500">Vendor</span>
                  <span className="capitalize">{device.vendor}</span>
                </div>
                {device.model && (
                  <div className="flex justify-between">
                    <span className="text-gray-500">Model</span>
                    <span>{device.model}</span>
                  </div>
                )}
                <div className="flex justify-between">
                  <span className="text-gray-500">Status</span>
                  <span className={device.is_connected ? 'text-green-600' : 'text-gray-400'}>
                    {device.is_connected ? '● Connected' : '○ Disconnected'}
                  </span>
                </div>
                {device.last_sync_at && (
                  <div className="flex justify-between">
                    <span className="text-gray-500">Last Sync</span>
                    <span className="text-sm">
                      {new Date(device.last_sync_at).toLocaleString()}
                    </span>
                  </div>
                )}
              </div>
              <div className="mt-4 flex space-x-2">
                <Button variant="outline" className="flex-1">Sync</Button>
                <Button variant="ghost" className="flex-1">Settings</Button>
              </div>
            </CardContent>
          </Card>
        ))}

        {devices.length === 0 && (
          <Card className="col-span-full">
            <CardContent className="text-center py-12">
              <p className="text-gray-500 mb-4">No devices connected yet</p>
              <Button variant="primary">Connect Your First Device</Button>
            </CardContent>
          </Card>
        )}
      </div>
    </div>
  );
}
