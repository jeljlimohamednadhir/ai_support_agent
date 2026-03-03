/**
 * LowConfidenceTable Component
 * Table for correcting low confidence predictions
 */
import React, { useState, useEffect } from 'react';
import { Save } from 'lucide-react';
import { classificationMLService } from '../../services/classificationMLService';
import type { PredictionResult } from '../../services/classificationMLService';

interface LowConfidenceTableProps {
  predictions: PredictionResult[];
  onCorrection: (ticketId: string, correctedLabel: string, originalLabel: string) => void;
}

export const LowConfidenceTable: React.FC<LowConfidenceTableProps> = ({ predictions, onCorrection }) => {
  const [corrections, setCorrections] = useState<Record<string, string>>({});
  const [availableClasses, setAvailableClasses] = useState<string[]>([]);

  // Charger les classes disponibles depuis le modèle
  useEffect(() => {
    classificationMLService.getModelInfo().then(info => {
      if (info.classes && info.classes.length > 0) {
        setAvailableClasses(info.classes);
      }
    }).catch(err => {
      console.error('Failed to load classes:', err);
    });
  }, []);

  const handleCorrection = (ticketId: string) => {
    const correctedLabel = corrections[ticketId];
    const originalLabel = predictions.find(p => p.ticket_id === ticketId)?.predicted_label;
    
    if (correctedLabel && originalLabel) {
      onCorrection(ticketId, correctedLabel, originalLabel);
      alert('Correction sauvegardée');
    }
  };

  if (predictions.length === 0) {
    return (
      <div className="bg-green-50 dark:bg-green-900/20 border border-green-200 dark:border-green-800 rounded-lg p-6 text-center">
        <p className="text-green-800 dark:text-green-200">
          Aucune prédiction à faible confiance. Tous les tickets ont été acceptés !
        </p>
      </div>
    );
  }

  return (
    <div className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700">
      <div className="p-4 border-b border-gray-200 dark:border-gray-700">
        <h3 className="text-lg font-semibold">Prédictions à Faible Confiance</h3>
        <p className="text-sm text-gray-600 dark:text-gray-400 mt-1">
          {predictions.length} tickets nécessitent une validation manuelle
        </p>
      </div>

      <div className="overflow-x-auto">
        <table className="w-full">
          <thead className="bg-gray-50 dark:bg-gray-900">
            <tr>
              <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase">
                Ticket ID
              </th>
              <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase">
                Prédiction
              </th>
              <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase">
                Confiance
              </th>
              <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase">
                Correction
              </th>
              <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase">
                Action
              </th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-200 dark:divide-gray-700">
            {predictions.slice(0, 50).map(pred => (
              <tr key={pred.ticket_id} className="hover:bg-gray-50 dark:hover:bg-gray-900/50">
                <td className="px-4 py-3 text-sm font-mono">
                  {pred.ticket_id}
                </td>
                <td className="px-4 py-3 text-sm">
                  {pred.predicted_label}
                </td>
                <td className="px-4 py-3 text-sm">
                  <span className={`px-2 py-1 rounded text-xs font-semibold ${
                    pred.confidence < 0.3 ? 'bg-red-100 text-red-800 dark:bg-red-900/20 dark:text-red-200' :
                    pred.confidence < 0.5 ? 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900/20 dark:text-yellow-200' :
                    'bg-orange-100 text-orange-800 dark:bg-orange-900/20 dark:text-orange-200'
                  }`}>
                    {(pred.confidence * 100).toFixed(1)}%
                  </span>
                </td>
                <td className="px-4 py-3">
                  {availableClasses.length > 0 ? (
                    <select
                      value={corrections[pred.ticket_id] || ''}
                      onChange={(e) => setCorrections({ ...corrections, [pred.ticket_id]: e.target.value })}
                      className="w-full px-3 py-1 border border-gray-300 dark:border-gray-600 rounded bg-white dark:bg-gray-900 text-sm"
                    >
                      <option value="">-- Sélectionner --</option>
                      {availableClasses.map(cls => (
                        <option key={cls} value={cls}>{cls}</option>
                      ))}
                    </select>
                  ) : (
                    <input
                      type="text"
                      value={corrections[pred.ticket_id] || ''}
                      onChange={(e) => setCorrections({ ...corrections, [pred.ticket_id]: e.target.value })}
                      placeholder="Label corrigé..."
                      className="w-full px-3 py-1 border border-gray-300 dark:border-gray-600 rounded bg-white dark:bg-gray-900 text-sm"
                    />
                  )}
                </td>
                <td className="px-4 py-3">
                  <button
                    onClick={() => handleCorrection(pred.ticket_id)}
                    disabled={!corrections[pred.ticket_id]}
                    className="px-3 py-1 bg-blue-600 text-white rounded hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-1 text-sm"
                  >
                    <Save className="w-3 h-3" />
                    Sauver
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {predictions.length > 50 && (
        <div className="p-4 border-t border-gray-200 dark:border-gray-700 text-center text-sm text-gray-600 dark:text-gray-400">
          Affichage des 50 premiers tickets. {predictions.length - 50} autres tickets nécessitent une validation.
        </div>
      )}
    </div>
  );
};
