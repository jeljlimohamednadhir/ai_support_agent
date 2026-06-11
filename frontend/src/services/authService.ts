/**
 * Authentication Service
 * Handles API calls for authentication and user management
 */
import axios, { AxiosInstance } from 'axios';

const API_URL = import.meta.env.VITE_API_URL || '/api/v1';

export interface User {
  id: number;
  username: string;
  email: string;
  full_name: string | null;
  role: 'USER' | 'EXPERT' | 'ADMIN';
  is_active: boolean;
  created_at: string;
  last_login: string | null;
}

export interface LoginResponse {
  access_token: string;
  token_type: string;
}

export interface UserCreate {
  username: string;
  email: string;
  full_name?: string;
  password: string;
  role: 'USER' | 'EXPERT' | 'ADMIN';
}

export interface UserUpdate {
  email?: string;
  full_name?: string;
  role?: 'USER' | 'EXPERT' | 'ADMIN';
  is_active?: boolean;
  password?: string;
}

export interface PasswordChange {
  old_password: string;
  new_password: string;
}

class AuthService {
  private api: AxiosInstance;
  private token: string | null = null;

  constructor() {
    this.api = axios.create({
      baseURL: API_URL,
      headers: {
        'Content-Type': 'application/json',
      },
    });

    // Add request interceptor to include token
    this.api.interceptors.request.use(
      (config) => {
        if (this.token) {
          config.headers.Authorization = `Bearer ${this.token}`;
        }
        return config;
      },
      (error) => Promise.reject(error)
    );

    // Add response interceptor for error handling
    this.api.interceptors.response.use(
      (response) => response,
      (error) => {
        if (error.response?.status === 401) {
          // Token expired or invalid
          this.token = null;
          localStorage.removeItem('auth_token');
          window.location.href = '/login';
        }
        return Promise.reject(error);
      }
    );
  }

  setToken(token: string | null) {
    this.token = token;
  }

  async login(username: string, password: string): Promise<{ token: string; user: User }> {
    const formData = new FormData();
    formData.append('username', username);
    formData.append('password', password);

    const response = await this.api.post<LoginResponse>('/auth/login', formData, {
      headers: {
        'Content-Type': 'application/x-www-form-urlencoded',
      },
    });

    this.token = response.data.access_token;
    
    // Get user info
    const user = await this.getCurrentUser();

    return {
      token: response.data.access_token,
      user,
    };
  }

  async logout(): Promise<void> {
    await this.api.post('/auth/logout');
    this.token = null;
  }

  async getCurrentUser(): Promise<User> {
    const response = await this.api.get<User>('/auth/me');
    return response.data;
  }

  async changePassword(data: PasswordChange): Promise<void> {
    await this.api.post('/auth/change-password', data);
  }

  // Admin endpoints
  async createUser(data: UserCreate): Promise<User> {
    const response = await this.api.post<User>('/auth/users', data);
    return response.data;
  }

  async listUsers(skip: number = 0, limit: number = 100): Promise<User[]> {
    const response = await this.api.get<User[]>('/auth/users', {
      params: { skip, limit },
    });
    return response.data;
  }

  async getUser(userId: number): Promise<User> {
    const response = await this.api.get<User>(`/auth/users/${userId}`);
    return response.data;
  }

  async updateUser(userId: number, data: UserUpdate): Promise<User> {
    const response = await this.api.put<User>(`/auth/users/${userId}`, data);
    return response.data;
  }

  async deleteUser(userId: number): Promise<void> {
    await this.api.delete(`/auth/users/${userId}`);
  }
}

export const authService = new AuthService();
