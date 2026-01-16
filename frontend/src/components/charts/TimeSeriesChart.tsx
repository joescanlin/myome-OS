import { useMemo } from 'react';
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  ReferenceLine,
} from 'recharts';
import { format } from 'date-fns';

interface DataPoint {
  timestamp: string;
  value: number;
}

interface ReferenceLineConfig {
  value: number;
  label: string;
  color: string;
}

interface TimeSeriesChartProps {
  data: DataPoint[];
  color?: string;
  unit?: string;
  referenceLines?: ReferenceLineConfig[];
  height?: number;
}

export function TimeSeriesChart({
  data,
  color = '#E74C3C',
  unit = '',
  referenceLines = [],
  height = 300,
}: TimeSeriesChartProps) {
  const chartData = useMemo(() => {
    return data.map((d) => ({
      ...d,
      time: new Date(d.timestamp).getTime(),
    }));
  }, [data]);

  if (data.length === 0) {
    return (
      <div className="flex items-center justify-center h-64 text-gray-400">
        No data available
      </div>
    );
  }

  return (
    <ResponsiveContainer width="100%" height={height}>
      <LineChart data={chartData} margin={{ top: 10, right: 30, left: 0, bottom: 0 }}>
        <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
        <XAxis
          dataKey="time"
          type="number"
          domain={['dataMin', 'dataMax']}
          tickFormatter={(tick) => format(new Date(tick), 'MMM d')}
          stroke="#9ca3af"
          fontSize={12}
        />
        <YAxis stroke="#9ca3af" fontSize={12} />
        <Tooltip
          labelFormatter={(label) => format(new Date(label), 'MMM d, yyyy HH:mm')}
          formatter={(value: number) => [`${value.toFixed(1)} ${unit}`, 'Value']}
          contentStyle={{
            backgroundColor: 'white',
            border: '1px solid #e5e7eb',
            borderRadius: '8px',
          }}
        />
        {referenceLines.map((line, idx) => (
          <ReferenceLine
            key={idx}
            y={line.value}
            stroke={line.color}
            strokeDasharray="5 5"
            label={{ value: line.label, position: 'right', fill: line.color, fontSize: 12 }}
          />
        ))}
        <Line
          type="monotone"
          dataKey="value"
          stroke={color}
          strokeWidth={2}
          dot={false}
          activeDot={{ r: 4, fill: color }}
        />
      </LineChart>
    </ResponsiveContainer>
  );
}
