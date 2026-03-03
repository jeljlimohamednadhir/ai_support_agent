/**
 * KeywordsConfigEditor Component
 * Edit keywords configuration for categorization
 */
import React, { useState, useEffect } from 'react';
import { Save, RotateCcw, Plus, Trash2 } from 'lucide-react';
import { classificationMLService, type KeywordsConfig } from '../../services/classificationMLService';

export const KeywordsConfigEditor: React.FC = () => {
  const [config, setConfig] = useState<KeywordsConfig>({ categories: {} });
  const [loading, setLoading] = useState(false);
  const [newCategory, setNewCategory] = useState('');
  const [newKeyword, setNewKeyword] = useState<Record<string, string>>({});

  useEffect(() => {
    loadConfig();
  }, []);

  const loadConfig = async () => {
    try {
      const data = await classificationMLService.getKeywordsConfig();
      setConfig(data);
    } catch (err) {
      console.error('Failed to load config:', err);
    }
  };

  const handleSave = async () => {
    setLoading(true);
    try {
      await classificationMLService.saveKeywordsConfig(config);
      alert('Configuration sauvegardée avec succès');
    } catch (err: any) {
      alert('Erreur lors de la sauvegarde: ' + (err.response?.data?.detail || err.message));
    } finally {
      setLoading(false);
    }
  };

  const handleReset = async () => {
    if (!confirm('Réinitialiser à la configuration par défaut ?')) return;
    
    setLoading(true);
    try {
      await classificationMLService.resetKeywordsConfig();
      await loadConfig();
      alert('Configuration réinitialisée');
    } catch (err: any) {
      alert('Erreur lors de la réinitialisation: ' + (err.response?.data?.detail || err.message));
    } finally {
      setLoading(false);
    }
  };

  const addCategory = () => {
    if (!newCategory.trim()) return;
    setConfig({
      categories: {
        ...config.categories,
        [newCategory]: []
      }
    });
    setNewCategory('');
  };

  const deleteCategory = (category: string) => {
    const { [category]: _, ...rest } = config.categories;
    setConfig({ categories: rest });
  };

  const addKeyword = (category: string) => {
    const keyword = newKeyword[category]?.trim();
    if (!keyword) return;

    setConfig({
      categories: {
        ...config.categories,
        [category]: [...(config.categories[category] || []), keyword]
      }
    });
    setNewKeyword({ ...newKeyword, [category]: '' });
  };

  const deleteKeyword = (category: string, keyword: string) => {
    setConfig({
      categories: {
        ...config.categories,
        [category]: config.categories[category].filter(k => k !== keyword)
      }
    });
  };

  return (
    <div className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 p-6 space-y-6">
      <div className="flex items-center justify-between">
        <h3 className="text-lg font-semibold">Configuration des Mots-Clés</h3>
        <div className="flex gap-2">
          <button
            onClick={handleReset}
            disabled={loading}
            className="px-4 py-2 bg-gray-600 text-white rounded-lg hover:bg-gray-700 disabled:opacity-50 flex items-center gap-2"
          >
            <RotateCcw className="w-4 h-4" />
            Réinitialiser
          </button>
          <button
            onClick={handleSave}
            disabled={loading}
            className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 flex items-center gap-2"
          >
            <Save className="w-4 h-4" />
            Sauvegarder
          </button>
        </div>
      </div>

      <div className="space-y-4">
        {Object.entries(config.categories).map(([category, keywords]) => (
          <div key={category} className="border border-gray-200 dark:border-gray-700 rounded-lg p-4">
            <div className="flex items-center justify-between mb-3">
              <h4 className="font-semibold text-sm">{category}</h4>
              <button
                onClick={() => deleteCategory(category)}
                className="p-1 text-red-600 hover:bg-red-50 dark:hover:bg-red-900/20 rounded"
              >
                <Trash2 className="w-4 h-4" />
              </button>
            </div>

            <div className="flex flex-wrap gap-2 mb-3">
              {keywords.map(keyword => (
                <span
                  key={keyword}
                  className="px-3 py-1 bg-blue-100 dark:bg-blue-900/20 text-blue-800 dark:text-blue-200 rounded-full text-sm flex items-center gap-2"
                >
                  {keyword}
                  <button
                    onClick={() => deleteKeyword(category, keyword)}
                    className="hover:text-red-600"
                  >
                    ×
                  </button>
                </span>
              ))}
            </div>

            <div className="flex gap-2">
              <input
                type="text"
                value={newKeyword[category] || ''}
                onChange={(e) => setNewKeyword({ ...newKeyword, [category]: e.target.value })}
                onKeyPress={(e) => e.key === 'Enter' && addKeyword(category)}
                placeholder="Ajouter un mot-clé..."
                className="flex-1 px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-900 text-sm"
              />
              <button
                onClick={() => addKeyword(category)}
                className="px-3 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700"
              >
                <Plus className="w-4 h-4" />
              </button>
            </div>
          </div>
        ))}
      </div>

      <div className="border-t border-gray-200 dark:border-gray-700 pt-4">
        <div className="flex gap-2">
          <input
            type="text"
            value={newCategory}
            onChange={(e) => setNewCategory(e.target.value)}
            onKeyPress={(e) => e.key === 'Enter' && addCategory()}
            placeholder="Nouvelle catégorie..."
            className="flex-1 px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-900"
          />
          <button
            onClick={addCategory}
            className="px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 flex items-center gap-2"
          >
            <Plus className="w-4 h-4" />
            Ajouter catégorie
          </button>
        </div>
      </div>
    </div>
  );
};
