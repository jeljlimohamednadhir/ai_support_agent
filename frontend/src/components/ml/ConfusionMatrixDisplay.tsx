/**
 * ConfusionMatrixDisplay Component
 * Displays confusion matrix as heatmap
 */
import React from 'react';

interface ConfusionMatrixProps {
  matrix: number[][];
  classes: string[];
}

export const ConfusionMatrixDisplay: React.FC<ConfusionMatrixProps> = ({ matrix, classes }) => {
  const maxValue = Math.max(...matrix.flat());

  const getColor = (value: number) => {
    const intensity = value / maxValue;
    const blue = Math.floor(59 + intensity * (37 - 59));
    const green = Math.floor(130 + intensity * (99 - 130));
    const red = Math.floor(246 + intensity * (239 - 246));
    return `rgb(${red}, ${green}, ${blue})`;
  };

  return (
    <div className="bg-white dark:bg-gray-800 rounded-lg p-6 border border-gray-200 dark:border-gray-700">
      <h3 className="text-lg font-semibold mb-4">Matrice de Confusion</h3>
      <div className="overflow-x-auto">
        <div className="inline-block min-w-full">
          <div className="grid gap-1" style={{ gridTemplateColumns: `100px repeat(${classes.length}, 60px)` }}>
            {/* Header */}
            <div className="p-2"></div>
            {classes.map((cls, i) => (
              <div key={i} className="p-2 text-center text-xs font-semibold bg-gray-100 dark:bg-gray-700 rounded">
                {cls.length > 8 ? cls.substring(0, 8) + '...' : cls}
              </div>
            ))}

            {/* Rows */}
            {matrix.map((row, i) => (
              <React.Fragment key={i}>
                <div className="p-2 text-xs font-semibold bg-gray-100 dark:bg-gray-700 rounded flex items-center">
                  {classes[i].length > 12 ? classes[i].substring(0, 12) + '...' : classes[i]}
                </div>
                {row.map((value, j) => (
                  <div
                    key={j}
                    className="p-2 text-center text-sm font-medium rounded relative"
                    style={{ backgroundColor: getColor(value) }}
                    title={`${classes[i]} → ${classes[j]}: ${value}`}
                  >
                    <span className={value > maxValue * 0.5 ? 'text-white' : 'text-gray-900'}>
                      {value}
                    </span>
                  </div>
                ))}
              </React.Fragment>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
};
