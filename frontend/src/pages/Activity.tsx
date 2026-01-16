import { Card, CardHeader, CardTitle, CardContent } from '../components/common/Card';

export function Activity() {
  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold text-gray-900">Activity</h1>

      <Card>
        <CardHeader>
          <CardTitle>Coming Soon</CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-gray-500">
            Activity tracking will be available in a future update. This will include:
          </p>
          <ul className="mt-4 space-y-2 text-gray-600">
            <li>- Steps and distance tracking</li>
            <li>- Workout sessions</li>
            <li>- Active minutes and calories</li>
            <li>- Exercise trends and goals</li>
          </ul>
        </CardContent>
      </Card>
    </div>
  );
}
