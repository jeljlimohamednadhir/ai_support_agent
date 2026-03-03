/**
 * TimelineChart Component
 * Displays timeseries data
 */
import React from 'react';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from 'recharts';

interface TimeseriesPoint {
  date: string;
  volume: number;
  label?: string;
}

interface TimelineChartProps {
  data: TimeseriesPoint[];
}

export const TimelineChart: React.FC<TimelineChartProps> = ({ data }) => {
  // Group by label if exists
  const hasLabels = data.some(d => d.label);
  
  if (hasLabels) {
    // Transform data for multiple lines
    const labels = Array.from(new Set(data.map(d => d.label).filter(Boolean)));
    const dates = Array.from(new Set(data.map(d => d.date)));
    
    const chartData = dates.map(date => {
      const point: any = { date };
      labels.forEach(label => {
        const value = data.find(d => d.date === date && d.label === label);
        point[label || 'unknown'] = value?.volume || 0;
      });
      return point;
    });

    const colors = ['#3B82F6', '#EF4444', '#10B981', '#F59E0B', '#8B5CF6', '#EC4899'];

    return (
      <ResponsiveContainer width="100%" height={400}>
        <LineChart data={chartData}>
          <CartesianGrid strokeDasharray="3 3" />
          <XAxis dataKey="date" angle={-45} textAnchor="end" height={80} />
          <YAxis />
          <Tooltip />
          <Legend />
          {labels.map((label, i) => (
            <Line
              key={label}
              type="monotone"
              dataKey={label || 'unknown'}
              stroke={colors[i % colors.length]}
              strokeWidth={2}
              dot={{ r: 3 }}
            />
          ))}
        </LineChart>
      </ResponsiveContainer>
    );
  }

  return (
    <ResponsiveContainer width="100%" height={400}>
      <LineChart data={data}>
        <CartesianGrid strokeDasharray="3 3" />
        <XAxis dataKey="date" angle={-45} textAnchor="end" height={80} />
        <YAxis />
        <Tooltip />
        <Legend />
        <Line type="monotone" dataKey="volume" stroke="#3B82F6" strokeWidth={2} dot={{ r: 4 }} />
      </LineChart>
    </ResponsiveContainer>
  );
};
