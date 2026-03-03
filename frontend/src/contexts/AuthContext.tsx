/**
 * Authentication Context
 * Manages user authentication state, login/logout, and token persistence
 */
import React, { createContext, useContext, useState, useEffect, ReactNode } from 'react';
import { authService, User } from '../services/authService';

interface AuthContextType {
  user: User | null;
  token: string | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  login: (username: string, password: string) => Promise<void>;
  logout: () => Promise<void>;
  updateUser: (user: User) => void;
  hasRole: (role: 'USER' | 'EXPERT' | 'ADMIN') => boolean;
  canCorrectML: boolean;
  isAdmin: boolean;
  isExpert: boolean;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
};

interface AuthProviderProps {
  children: ReactNode;
}

export const AuthProvider: React.FC<AuthProviderProps> = ({ children }) => {
  const [user, setUser] = useState<User | null>(null);
  const [token, setToken] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  // Load token and user from localStorage on mount
  useEffect(() => {
    const loadAuth = async () => {
      try {
        const storedToken = localStorage.getItem('auth_token');
        if (storedToken) {
          authService.setToken(storedToken);
          const currentUser = await authService.getCurrentUser();
          setUser(currentUser);
          setToken(storedToken);
        }
      } catch (error) {
        console.error('Failed to load auth:', error);
        // Clear invalid token
        localStorage.removeItem('auth_token');
        authService.setToken(null);
      } finally {
        setIsLoading(false);
      }
    };

    loadAuth();
  }, []);

  const login = async (username: string, password: string) => {
    try {
      const { token: newToken, user: newUser } = await authService.login(username, password);
      localStorage.setItem('auth_token', newToken);
      authService.setToken(newToken);
      setToken(newToken);
      setUser(newUser);
    } catch (error) {
      console.error('Login failed:', error);
      throw error;
    }
  };

  const logout = async () => {
    try {
      await authService.logout();
    } catch (error) {
      console.error('Logout error:', error);
    } finally {
      localStorage.removeItem('auth_token');
      authService.setToken(null);
      setToken(null);
      setUser(null);
    }
  };

  const updateUser = (updatedUser: User) => {
    setUser(updatedUser);
  };

  const hasRole = (role: 'USER' | 'EXPERT' | 'ADMIN'): boolean => {
    if (!user) return false;
    
    const userRole = user.role.toUpperCase();
    
    // Admin has all roles
    if (userRole === 'ADMIN') return true;
    
    // Expert has EXPERT and USER roles
    if (userRole === 'EXPERT' && (role === 'EXPERT' || role === 'USER')) return true;
    
    // User only has USER role
    return userRole === role;
  };

  const value: AuthContextType = {
    user,
    token,
    isAuthenticated: !!user && !!token,
    isLoading,
    login,
    logout,
    updateUser,
    hasRole,
    canCorrectML: user?.role.toUpperCase() === 'EXPERT' || user?.role.toUpperCase() === 'ADMIN',
    isAdmin: user?.role.toUpperCase() === 'ADMIN',
    isExpert: user?.role.toUpperCase() === 'EXPERT' || user?.role.toUpperCase() === 'ADMIN',
  };

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
};
