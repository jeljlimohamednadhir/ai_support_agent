/**
 * User Management Page (Admin Only)
 * CRUD operations for user management
 */
import React, { useState, useEffect } from 'react';
import { authService, User, UserCreate, UserUpdate } from '../services/authService';
import {
  Users,
  Plus,
  Edit2,
  Trash2,
  X,
  Save,
  Shield,
  Mail,
  User as UserIcon,
  CheckCircle,
  XCircle,
  Eye,
  EyeOff,
} from 'lucide-react';

export const UserManagementPage: React.FC = () => {
  const [users, setUsers] = useState<User[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState('');
  const [isCreating, setIsCreating] = useState(false);
  const [editingUser, setEditingUser] = useState<User | null>(null);
  const [showPassword, setShowPassword] = useState(false);

  const [newUser, setNewUser] = useState<UserCreate>({
    username: '',
    email: '',
    full_name: '',
    password: '',
    role: 'USER',
  });

  const [updateData, setUpdateData] = useState<UserUpdate>({});

  useEffect(() => {
    // Set token on authService from localStorage before fetching
    const storedToken = localStorage.getItem('auth_token')
    if (storedToken) {
      authService.setToken(storedToken)
    }
    loadUsers();
  }, []);

  const loadUsers = async () => {
    try {
      setIsLoading(true);
      const data = await authService.listUsers();
      setUsers(data);
      setError('');
    } catch (err: any) {
      console.error('Error loading users:', err);
      setError('Erreur lors du chargement des utilisateurs');
    } finally {
      setIsLoading(false);
    }
  };

  const handleCreateUser = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      await authService.createUser(newUser);
      setNewUser({
        username: '',
        email: '',
        full_name: '',
        password: '',
        role: 'USER',
      });
      setIsCreating(false);
      await loadUsers();
    } catch (err: any) {
      console.error('Error creating user:', err);
      if (err.response?.data?.detail) {
        setError(err.response.data.detail);
      } else {
        setError('Erreur lors de la création de l\'utilisateur');
      }
    }
  };

  const handleUpdateUser = async (userId: number) => {
    try {
      await authService.updateUser(userId, updateData);
      setEditingUser(null);
      setUpdateData({});
      await loadUsers();
    } catch (err: any) {
      console.error('Error updating user:', err);
      setError('Erreur lors de la mise à jour');
    }
  };

  const handleDeleteUser = async (userId: number, username: string) => {
    if (!confirm(`Êtes-vous sûr de vouloir supprimer l'utilisateur "${username}" ?`)) {
      return;
    }

    try {
      await authService.deleteUser(userId);
      await loadUsers();
    } catch (err: any) {
      console.error('Error deleting user:', err);
      if (err.response?.data?.detail) {
        setError(err.response.data.detail);
      } else {
        setError('Erreur lors de la suppression');
      }
    }
  };

  const startEdit = (user: User) => {
    setEditingUser(user);
    setUpdateData({
      email: user.email,
      full_name: user.full_name || '',
      role: user.role,
      is_active: user.is_active,
    });
  };

  const getRoleBadge = (role: string) => {
    const colors = {
      ADMIN: 'bg-purple-100 text-purple-800',
      EXPERT: 'bg-blue-100 text-blue-800',
      USER: 'bg-green-100 text-green-800',
    };
    return colors[role as keyof typeof colors] || 'bg-gray-100 text-gray-800';
  };

  if (isLoading) {
    return (
      <div className="flex items-center justify-center min-h-screen dark:bg-gray-900">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
      </div>
    );
  }

  return (
    <div className="max-w-7xl mx-auto p-6 space-y-6 min-h-screen dark:bg-gray-900">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <Users className="w-8 h-8 text-blue-600" />
          <div>
            <h1 className="text-2xl font-bold text-gray-900 dark:text-white">Gestion des utilisateurs</h1>
            <p className="text-gray-600 dark:text-gray-400">{users.length} utilisateur(s)</p>
          </div>
        </div>
        <button
          onClick={() => setIsCreating(true)}
          className="flex items-center gap-2 px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg transition-colors"
        >
          <Plus className="w-5 h-5" />
          Créer un utilisateur
        </button>
      </div>

      {/* Error Message */}
      {error && (
        <div className="bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg p-4">
          <p className="text-red-800 dark:text-red-300">{error}</p>
          <button
            onClick={() => setError('')}
            className="text-red-600 underline text-sm mt-1"
          >
            Fermer
          </button>
        </div>
      )}

      {/* Create User Form */}
      {isCreating && (
        <div className="bg-white dark:bg-gray-800 rounded-lg shadow-sm border border-gray-200 dark:border-gray-700 p-6">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-lg font-semibold text-gray-900 dark:text-white">Créer un nouvel utilisateur</h2>
            <button
              onClick={() => setIsCreating(false)}
              className="text-gray-400 hover:text-gray-600"
            >
              <X className="w-5 h-5" />
            </button>
          </div>
          <form onSubmit={handleCreateUser} className="space-y-4">
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Nom d'utilisateur *
                </label>
                <input
                  type="text"
                  value={newUser.username}
                  onChange={(e) => setNewUser({ ...newUser, username: e.target.value })}
                  required
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">Email *</label>
                <input
                  type="email"
                  value={newUser.email}
                  onChange={(e) => setNewUser({ ...newUser, email: e.target.value })}
                  required
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">Nom complet</label>
                <input
                  type="text"
                  value={newUser.full_name}
                  onChange={(e) => setNewUser({ ...newUser, full_name: e.target.value })}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">Rôle *</label>
                <select
                  value={newUser.role}
                  onChange={(e) =>
                    setNewUser({ ...newUser, role: e.target.value as 'USER' | 'EXPERT' | 'ADMIN' })
                  }
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                >
                  <option value="USER">Utilisateur</option>
                  <option value="EXPERT">Expert</option>
                  <option value="ADMIN">Administrateur</option>
                </select>
              </div>
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Mot de passe *
              </label>
              <div className="relative">
                <input
                  type={showPassword ? 'text' : 'password'}
                  value={newUser.password}
                  onChange={(e) => setNewUser({ ...newUser, password: e.target.value })}
                  required
                  minLength={8}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent pr-10"
                />
                <button
                  type="button"
                  onClick={() => setShowPassword(!showPassword)}
                  className="absolute right-2 top-1/2 -translate-y-1/2 text-gray-400 hover:text-gray-600"
                >
                  {showPassword ? <EyeOff className="w-5 h-5" /> : <Eye className="w-5 h-5" />}
                </button>
              </div>
              <p className="text-xs text-gray-500 mt-1">
                Min. 8 caractères, avec majuscule, minuscule et chiffre
              </p>
            </div>
            <div className="flex gap-3">
              <button
                type="submit"
                className="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg transition-colors"
              >
                Créer l'utilisateur
              </button>
              <button
                type="button"
                onClick={() => setIsCreating(false)}
                className="px-4 py-2 bg-gray-200 hover:bg-gray-300 text-gray-700 rounded-lg transition-colors"
              >
                Annuler
              </button>
            </div>
          </form>
        </div>
      )}

      {/* Users Table */}
      <div className="bg-white dark:bg-gray-800 rounded-lg shadow-sm border border-gray-200 dark:border-gray-700 overflow-hidden">
        <table className="w-full">
          <thead className="bg-gray-50 dark:bg-gray-700 border-b border-gray-200 dark:border-gray-600">
            <tr>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                Utilisateur
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                Email
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                Rôle
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                Statut
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                Dernière connexion
              </th>
              <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                Actions
              </th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-200 dark:divide-gray-700">
            {users.map((user) => (
              <tr key={user.id} className="hover:bg-gray-50 dark:hover:bg-gray-700/50 dark:bg-gray-800">
                {editingUser?.id === user.id ? (
                  <>
                    <td className="px-6 py-4">
                      <div className="flex items-center gap-2">
                        <UserIcon className="w-5 h-5 text-gray-400" />
                        <div>
                          <div className="font-medium text-gray-900 dark:text-white">{user.username}</div>
                          <input
                            type="text"
                            value={updateData.full_name || ''}
                            onChange={(e) =>
                              setUpdateData({ ...updateData, full_name: e.target.value })
                            }
                            className="text-sm px-2 py-1 border border-gray-300 dark:border-gray-600 dark:bg-gray-700 dark:text-white rounded mt-1"
                            placeholder="Nom complet"
                          />
                        </div>
                      </div>
                    </td>
                    <td className="px-6 py-4">
                      <input
                        type="email"
                        value={updateData.email || ''}
                        onChange={(e) => setUpdateData({ ...updateData, email: e.target.value })}
                        className="px-2 py-1 border border-gray-300 rounded w-full"
                      />
                    </td>
                    <td className="px-6 py-4">
                      <select
                        value={updateData.role || user.role}
                        onChange={(e) =>
                          setUpdateData({
                            ...updateData,
                            role: e.target.value as 'USER' | 'EXPERT' | 'ADMIN',
                          })
                        }
                        className="px-2 py-1 border border-gray-300 rounded"
                      >
                        <option value="USER">Utilisateur</option>
                        <option value="EXPERT">Expert</option>
                        <option value="ADMIN">Admin</option>
                      </select>
                    </td>
                    <td className="px-6 py-4">
                      <label className="flex items-center gap-2">
                        <input
                          type="checkbox"
                          checked={updateData.is_active ?? user.is_active}
                          onChange={(e) =>
                            setUpdateData({ ...updateData, is_active: e.target.checked })
                          }
                          className="rounded"
                        />
                        <span className="text-sm">Actif</span>
                      </label>
                    </td>
                    <td className="px-6 py-4"></td>
                    <td className="px-6 py-4">
                      <div className="flex items-center justify-end gap-2">
                        <button
                          onClick={() => handleUpdateUser(user.id)}
                          className="p-1 text-green-600 hover:text-green-700"
                          title="Enregistrer"
                        >
                          <Save className="w-5 h-5" />
                        </button>
                        <button
                          onClick={() => {
                            setEditingUser(null);
                            setUpdateData({});
                          }}
                          className="p-1 text-gray-600 hover:text-gray-700"
                          title="Annuler"
                        >
                          <X className="w-5 h-5" />
                        </button>
                      </div>
                    </td>
                  </>
                ) : (
                  <>
                    <td className="px-6 py-4">
                      <div className="flex items-center gap-2">
                        <UserIcon className="w-5 h-5 text-gray-400" />
                        <div>
                          <div className="font-medium text-gray-900 dark:text-white">{user.username}</div>
                          <div className="text-sm text-gray-500 dark:text-gray-400">{user.full_name}</div>
                        </div>
                      </div>
                    </td>
                    <td className="px-6 py-4">
                      <div className="flex items-center gap-2 text-gray-700 dark:text-gray-300">
                        <Mail className="w-4 h-4 text-gray-400" />
                        {user.email}
                      </div>
                    </td>
                    <td className="px-6 py-4">
                      <span className={`px-2 py-1 rounded-full text-xs font-medium ${getRoleBadge(user.role)}`}>
                        <Shield className="w-3 h-3 inline mr-1" />
                        {user.role}
                      </span>
                    </td>
                    <td className="px-6 py-4">
                      {user.is_active ? (
                        <span className="flex items-center gap-1 text-green-700 text-sm">
                          <CheckCircle className="w-4 h-4" />
                          Actif
                        </span>
                      ) : (
                        <span className="flex items-center gap-1 text-red-700 text-sm">
                          <XCircle className="w-4 h-4" />
                          Inactif
                        </span>
                      )}
                    </td>
                    <td className="px-6 py-4 text-sm text-gray-500 dark:text-gray-400">
                      {user.last_login
                        ? new Date(user.last_login).toLocaleDateString('fr-FR')
                        : 'Jamais'}
                    </td>
                    <td className="px-6 py-4">
                      <div className="flex items-center justify-end gap-2">
                        <button
                          onClick={() => startEdit(user)}
                          className="p-1 text-blue-600 hover:text-blue-700"
                          title="Modifier"
                        >
                          <Edit2 className="w-5 h-5" />
                        </button>
                        <button
                          onClick={() => handleDeleteUser(user.id, user.username)}
                          className="p-1 text-red-600 hover:text-red-700"
                          title="Supprimer"
                        >
                          <Trash2 className="w-5 h-5" />
                        </button>
                      </div>
                    </td>
                  </>
                )}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
};
