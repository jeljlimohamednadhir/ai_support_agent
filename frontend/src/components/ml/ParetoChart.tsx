/**
 * ParetoChart Component
 * Displays Pareto chart with bar and cumulative line
 */
import React from 'react';
import { Bar, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer, ComposedChart } from 'recharts';

interface ParetoItem {
  label: string;
  volume: number;
  percentage: number;
  cumulative: number;
}

interface ParetoChartProps {
  data: ParetoItem[];
}

export const ParetoChart: React.FC<ParetoChartProps> = ({ data }) => {
  return (
    <div className="bg-white dark:bg-gray-800 rounded-lg p-6 border border-gray-200 dark:border-gray-700">
      <h3 className="text-lg font-semibold mb-4">Analyse Pareto</h3>
      <ResponsiveContainer width="100%" height={400}>
        <ComposedChart data={data}>
          <CartesianGrid strokeDasharray="3 3" />
          <XAxis 
            dataKey="label" 
            angle={-45} 
            textAnchor="end" 
            height={120}
            tick={{ fontSize: 12 }}
          />
          <YAxis yAxisId="left" label={{ value: 'Volume', angle: -90, position: 'insideLeft' }} />
          <YAxis 
            yAxisId="right" 
            orientation="right" 
            domain={[0, 100]}
            label={{ value: 'Cumul %', angle: 90, position: 'insideRight' }}
          />
          <Tooltip />
          <Legend />
          <Bar yAxisId="left" dataKey="volume" fill="#3B82F6" name="Volume" />
          <Line 
            yAxisId="right" 
            type="monotone" 
            dataKey="cumulative" 
            stroke="#EF4444" 
            strokeWidth={2}
            name="Cumul %"
            dot={{ r: 4 }}
          />
        </ComposedChart>
      </ResponsiveContainer>
    </div>
  );
};
