'use client';

import React, { createContext, useContext, useEffect, useState, ReactNode } from 'react';

interface Admin {
  id: number;
  username: string;
  is_active: boolean;
  is_super_admin: boolean;
  can_manage_players: boolean;
  can_manage_users: boolean;
  can_manage_leagues: boolean;
  can_manage_matches: boolean;
  can_view_analytics: boolean;
  created_at: string;
  last_login?: string;
}

interface AdminAuthContextType {
  admin: Admin | null;
  token: string | null;
  login: (username: string, password: string) => Promise<boolean>;
  logout: () => void;
  loading: boolean;
  error: string | null;
}

const AdminAuthContext = createContext<AdminAuthContextType | undefined>(undefined);

export function useAdminAuth() {
  const context = useContext(AdminAuthContext);
  if (context === undefined) {
    throw new Error('useAdminAuth must be used within an AdminAuthProvider');
  }
  return context;
}

interface AdminAuthProviderProps {
  children: ReactNode;
}

export function AdminAuthProvider({ children }: AdminAuthProviderProps) {
  const [admin, setAdmin] = useState<Admin | null>(null);
  const [token, setToken] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    // Check for existing admin token on mount
    const storedToken = localStorage.getItem('adminToken');
    if (storedToken) {
      setToken(storedToken);
      fetchCurrentAdmin(storedToken);
    } else {
      setLoading(false);
    }
  }, []);

  const fetchCurrentAdmin = async (authToken: string) => {
    try {
      const response = await fetch('/api/admin/auth/me', {
        headers: {
          'Authorization': `Bearer ${authToken}`,
        },
      });

      if (response.ok) {
        const adminData = await response.json();
        setAdmin(adminData);
      } else {
        // Token is invalid, clear it
        localStorage.removeItem('adminToken');
        setToken(null);
      }
    } catch (error) {
      console.error('Error fetching current admin:', error);
      localStorage.removeItem('adminToken');
      setToken(null);
    } finally {
      setLoading(false);
    }
  };

  const login = async (username: string, password: string): Promise<boolean> => {
    setLoading(true);
    setError(null);

    try {
      const formData = new FormData();
      formData.append('username', username);
      formData.append('password', password);

      const response = await fetch('/api/admin/auth/login', {
        method: 'POST',
        body: formData,
      });

      if (response.ok) {
        const data = await response.json();
        const { access_token } = data;
        
        setToken(access_token);
        localStorage.setItem('adminToken', access_token);
        
        // Fetch admin data
        await fetchCurrentAdmin(access_token);
        return true;
      } else {
        const errorData = await response.json();
        setError(errorData.detail || 'Admin login failed');
        return false;
      }
    } catch (error) {
      setError('Network error. Please try again.');
      return false;
    } finally {
      setLoading(false);
    }
  };

  const logout = () => {
    setAdmin(null);
    setToken(null);
    localStorage.removeItem('adminToken');
    window.location.href = '/admin/login';
  };

  const value = {
    admin,
    token,
    login,
    logout,
    loading,
    error,
  };

  return (
    <AdminAuthContext.Provider value={value}>
      {children}
    </AdminAuthContext.Provider>
  );
}
