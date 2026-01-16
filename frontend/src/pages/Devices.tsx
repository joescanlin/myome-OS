import { useEffect, useState } from 'react';
import { useSearchParams } from 'react-router-dom';
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

const SUPPORTED_PROVIDERS = [
  {
    id: 'whoop',
    name: 'Whoop',
    description: 'Sleep, recovery, HRV, strain, and workout data',
    icon: '💪',
    color: 'bg-black',
  },
  {
    id: 'withings',
    name: 'Withings',
    description: 'Weight, body composition, blood pressure, and sleep',
    icon: '⚖️',
    color: 'bg-green-600',
  },
];

export function Devices() {
  const [devices, setDevices] = useState<Device[]>([]);
  const [loading, setLoading] = useState(true);
  const [connecting, setConnecting] = useState<string | null>(null);
  const [searchParams, setSearchParams] = useSearchParams();

  // Handle OAuth callback results
  useEffect(() => {
    const connected = searchParams.get('connected');
    const error = searchParams.get('error');
    
    if (connected) {
      // Successfully connected a device
      loadDevices();
      // Clear the query params
      setSearchParams({});
    }
    
    if (error) {
      alert(`Connection failed: ${error}`);
      setSearchParams({});
    }
  }, [searchParams, setSearchParams]);

  const loadDevices = async () => {
    try {
      const data = await api.getDevices();
      setDevices(data);
    } catch (error) {
      console.error('Failed to load devices:', error);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadDevices();
  }, []);

  const handleConnect = async (provider: string) => {
    setConnecting(provider);
    try {
      const { authorization_url } = await api.initiateOAuth(provider as 'whoop' | 'withings');
      // Redirect to OAuth provider
      window.location.href = authorization_url;
    } catch (error) {
      console.error('Failed to initiate OAuth:', error);
      alert('Failed to connect. Make sure the integration is configured.');
      setConnecting(null);
    }
  };

  const handleSync = async (deviceId: string) => {
    try {
      await api.syncDevice(deviceId);
      alert('Sync started! Data will be updated shortly.');
      loadDevices();
    } catch (error) {
      console.error('Failed to sync device:', error);
      alert('Sync failed. Please try again.');
    }
  };

  const handleDisconnect = async (deviceId: string) => {
    if (!confirm('Are you sure you want to disconnect this device?')) {
      return;
    }
    
    try {
      await api.disconnectDevice(deviceId);
      loadDevices();
    } catch (error) {
      console.error('Failed to disconnect device:', error);
      alert('Failed to disconnect. Please try again.');
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-gray-500">Loading devices...</div>
      </div>
    );
  }

  // Check which providers are already connected
  const connectedVendors = new Set(devices.filter(d => d.is_connected).map(d => d.vendor));

  return (
    <div className="space-y-6">
      <div className="flex justify-between items-center">
        <h1 className="text-2xl font-bold text-gray-900">Connected Devices</h1>
      </div>

      {/* Connect New Device */}
      <Card>
        <CardHeader>
          <CardTitle>Connect a Device</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {SUPPORTED_PROVIDERS.map((provider) => {
              const isConnected = connectedVendors.has(provider.id);
              const isConnecting = connecting === provider.id;
              
              return (
                <div
                  key={provider.id}
                  className={`p-4 border rounded-lg ${isConnected ? 'bg-gray-50 border-gray-200' : 'border-gray-300 hover:border-primary-500'}`}
                >
                  <div className="flex items-start justify-between">
                    <div className="flex items-center space-x-3">
                      <span className="text-3xl">{provider.icon}</span>
                      <div>
                        <h3 className="font-semibold text-gray-900">{provider.name}</h3>
                        <p className="text-sm text-gray-500">{provider.description}</p>
                      </div>
                    </div>
                    {isConnected ? (
                      <span className="text-green-600 text-sm font-medium">Connected</span>
                    ) : (
                      <Button
                        variant="primary"
                        onClick={() => handleConnect(provider.id)}
                        disabled={isConnecting}
                      >
                        {isConnecting ? 'Connecting...' : 'Connect'}
                      </Button>
                    )}
                  </div>
                </div>
              );
            })}
          </div>
          <p className="mt-4 text-sm text-gray-500">
            More integrations coming soon: Apple Health, Garmin, Fitbit, Oura, and more.
          </p>
        </CardContent>
      </Card>

      {/* Connected Devices List */}
      {devices.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle>Your Devices</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              {devices.map((device) => (
                <div
                  key={device.id}
                  className="flex items-center justify-between p-4 bg-gray-50 rounded-lg"
                >
                  <div className="flex items-center space-x-4">
                    <div className={`w-3 h-3 rounded-full ${device.is_connected ? 'bg-green-500' : 'bg-gray-400'}`} />
                    <div>
                      <h3 className="font-medium text-gray-900">{device.name}</h3>
                      <p className="text-sm text-gray-500">
                        {device.vendor.charAt(0).toUpperCase() + device.vendor.slice(1)}
                        {device.model && ` - ${device.model}`}
                      </p>
                      {device.last_sync_at && (
                        <p className="text-xs text-gray-400">
                          Last sync: {new Date(device.last_sync_at).toLocaleString()}
                        </p>
                      )}
                    </div>
                  </div>
                  <div className="flex space-x-2">
                    {device.is_connected && (
                      <Button
                        variant="outline"
                        onClick={() => handleSync(device.id)}
                      >
                        Sync Now
                      </Button>
                    )}
                    <Button
                      variant="ghost"
                      onClick={() => handleDisconnect(device.id)}
                    >
                      Disconnect
                    </Button>
                  </div>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      )}

      {/* Manual Data Entry Fallback */}
      <Card>
        <CardHeader>
          <CardTitle>Manual Data Entry</CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-gray-600 mb-4">
            Don't have a supported device? You can manually enter your health data.
          </p>
          <Button variant="outline" onClick={() => window.location.href = '/add-reading'}>
            Add Manual Reading
          </Button>
        </CardContent>
      </Card>
    </div>
  );
}
