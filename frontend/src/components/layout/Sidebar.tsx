import { Link, useLocation } from 'react-router-dom';
import { clsx } from 'clsx';

const navigation = [
  { name: 'Dashboard', href: '/', icon: '📊' },
  { name: 'Heart Rate', href: '/heart-rate', icon: '❤️' },
  { name: 'Glucose', href: '/glucose', icon: '🩸' },
  { name: 'Sleep', href: '/sleep', icon: '😴' },
  { name: 'Activity', href: '/activity', icon: '🏃' },
  { name: 'Insights', href: '/insights', icon: '💡' },
  { name: 'Devices', href: '/devices', icon: '📱' },
  { name: 'Settings', href: '/settings', icon: '⚙️' },
];

export function Sidebar() {
  const location = useLocation();

  return (
    <aside className="w-64 bg-white border-r border-gray-200 min-h-screen">
      <div className="p-6">
        <Link to="/" className="flex items-center space-x-2">
          <span className="text-2xl font-bold text-primary-500">Myome</span>
        </Link>
      </div>
      
      <nav className="px-4">
        <ul className="space-y-1">
          {navigation.map((item) => {
            const isActive = location.pathname === item.href;
            return (
              <li key={item.name}>
                <Link
                  to={item.href}
                  className={clsx(
                    'flex items-center px-4 py-2 text-sm rounded-lg transition-colors',
                    isActive
                      ? 'bg-primary-50 text-primary-600 font-medium'
                      : 'text-gray-600 hover:bg-gray-50'
                  )}
                >
                  <span className="mr-3">{item.icon}</span>
                  {item.name}
                </Link>
              </li>
            );
          })}
        </ul>
      </nav>
    </aside>
  );
}
