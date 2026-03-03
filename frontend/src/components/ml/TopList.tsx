/**
 * TopList Component
 * Displays top items with bar visualization
 */
import React from 'react';
import { TrendingUp } from 'lucide-react';

interface TopListItem {
  name: string;
  value: number;
  percentage?: number;
}

interface TopListProps {
  title: string;
  items: TopListItem[];
  maxItems?: number;
}

export const TopList: React.FC<TopListProps> = ({ title, items, maxItems = 10 }) => {
  const displayItems = items.slice(0, maxItems);
  const maxValue = Math.max(...displayItems.map(i => i.value), 1);

  return (
    <div className="bg-white dark:bg-gray-800 rounded-lg p-6 border border-gray-200 dark:border-gray-700">
      <div className="flex items-center gap-2 mb-4">
        <TrendingUp className="w-5 h-5 text-blue-600 dark:text-blue-400" />
        <h3 className="text-lg font-semibold">{title}</h3>
      </div>

      <div className="space-y-3">
        {displayItems.map((item, index) => {
          const percentage = item.percentage !== undefined 
            ? item.percentage 
            : (item.value / maxValue) * 100;

          return (
            <div key={index} className="space-y-1">
              <div className="flex items-center justify-between text-sm">
                <span className="font-medium truncate flex-1 mr-2" title={item.name}>
                  {item.name}
                </span>
                <span className="text-gray-600 dark:text-gray-400 font-mono">
                  {item.value.toLocaleString()} 
                  {item.percentage !== undefined && (
                    <span className="ml-1 text-xs">({percentage.toFixed(1)}%)</span>
                  )}
                </span>
              </div>
              <div className="w-full bg-gray-200 dark:bg-gray-700 rounded-full h-2">
                <div
                  className="bg-blue-600 dark:bg-blue-500 h-2 rounded-full transition-all"
                  style={{ width: `${percentage}%` }}
                />
              </div>
            </div>
          );
        })}
      </div>

      {items.length > maxItems && (
        <p className="text-sm text-gray-500 dark:text-gray-400 mt-4 text-center">
          +{items.length - maxItems} autres items
        </p>
      )}
    </div>
  );
};
