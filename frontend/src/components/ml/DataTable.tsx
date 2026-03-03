/**
 * DataTable Component
 * Generic table for displaying data
 */
import React, { useState } from 'react';
import { ChevronLeft, ChevronRight } from 'lucide-react';

interface DataTableProps {
  data: Record<string, any>[];
  columns: string[];
  pageSize?: number;
}

export const DataTable: React.FC<DataTableProps> = ({ data, columns, pageSize = 20 }) => {
  const [currentPage, setCurrentPage] = useState(0);

  const totalPages = Math.ceil(data.length / pageSize);
  const startIdx = currentPage * pageSize;
  const endIdx = startIdx + pageSize;
  const currentData = data.slice(startIdx, endIdx);

  return (
    <div className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700">
      <div className="overflow-x-auto">
        <table className="w-full">
          <thead className="bg-gray-50 dark:bg-gray-900">
            <tr>
              {columns.map(col => (
                <th key={col} className="px-4 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                  {col}
                </th>
              ))}
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-200 dark:divide-gray-700">
            {currentData.map((row, i) => (
              <tr key={i} className="hover:bg-gray-50 dark:hover:bg-gray-900/50">
                {columns.map(col => (
                  <td key={col} className="px-4 py-3 text-sm text-gray-900 dark:text-gray-100">
                    {col === 'predicted_label' && row[col] ? (
                      <div className="flex items-center gap-2">
                        <span>{String(row[col])}</span>
                        {row.confidence && (
                          <span className={`text-xs px-2 py-0.5 rounded font-semibold ${
                            row.confidence >= 0.7 
                              ? 'bg-green-100 text-green-800 dark:bg-green-900/20 dark:text-green-200' 
                              : 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900/20 dark:text-yellow-200'
                          }`}>
                            {(row.confidence * 100).toFixed(0)}%
                          </span>
                        )}
                      </div>
                    ) : (
                      typeof row[col] === 'object' ? JSON.stringify(row[col]) : String(row[col] || '')
                    )}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {totalPages > 1 && (
        <div className="px-4 py-3 border-t border-gray-200 dark:border-gray-700 flex items-center justify-between">
          <div className="text-sm text-gray-600 dark:text-gray-400">
            Page {currentPage + 1} sur {totalPages} ({data.length} entrées)
          </div>
          <div className="flex gap-2">
            <button
              onClick={() => setCurrentPage(Math.max(0, currentPage - 1))}
              disabled={currentPage === 0}
              className="p-2 rounded border border-gray-300 dark:border-gray-600 disabled:opacity-50 disabled:cursor-not-allowed hover:bg-gray-50 dark:hover:bg-gray-800"
            >
              <ChevronLeft className="w-5 h-5" />
            </button>
            <button
              onClick={() => setCurrentPage(Math.min(totalPages - 1, currentPage + 1))}
              disabled={currentPage === totalPages - 1}
              className="p-2 rounded border border-gray-300 dark:border-gray-600 disabled:opacity-50 disabled:cursor-not-allowed hover:bg-gray-50 dark:hover:bg-gray-800"
            >
              <ChevronRight className="w-5 h-5" />
            </button>
          </div>
        </div>
      )}
    </div>
  );
};
