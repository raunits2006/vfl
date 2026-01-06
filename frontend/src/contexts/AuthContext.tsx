'use client';

import React, { createContext, useContext, useEffect, useState, ReactNode } from 'react';
import { User, AuthToken } from '../types/api';

interface AuthContextType {
  user: User | null;
  token: string | null;
  login: (username: string, password: string) => Promise<boolean>;
  register: (username: string, email: string, password: string) => Promise<boolean>;
  logout: () => void;
  loading: boolean;
  error: string | null;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

/**
 * Parse API error responses into human-readable messages.
 * Handles Pydantic validation errors (array of {type, loc, msg} objects),
 * standard {detail: string} errors, and unknown error shapes.
 */
function parseApiError(errorData: unknown): string {
  // Handle null/undefined
  if (!errorData) {
    return 'An unexpected error occurred';
  }

  // If it's already a string, return it
  if (typeof errorData === 'string') {
    return errorData;
  }

  // If it's an object with a 'detail' field
  if (typeof errorData === 'object' && 'detail' in errorData) {
    const detail = (errorData as { detail: unknown }).detail;

    // If detail is a string, return it directly
    if (typeof detail === 'string') {
      return detail;
    }

    // If detail is an array (Pydantic validation errors)
    if (Array.isArray(detail)) {
      const messages = detail
        .map((err: unknown) => {
          if (typeof err === 'object' && err !== null && 'msg' in err) {
            return (err as { msg: string }).msg;
          }
          return null;
        })
        .filter(Boolean);

      if (messages.length > 0) {
        return messages.join('. ');
      }
    }

    // If detail is some other object, try to stringify it meaningfully
    if (typeof detail === 'object' && detail !== null) {
      if ('msg' in detail) {
        return (detail as { msg: string }).msg;
      }
    }
  }

  // Last resort: generic message
  return 'An unexpected error occurred';
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (context === undefined) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
}

interface AuthProviderProps {
  children: ReactNode;
}

export function AuthProvider({ children }: AuthProviderProps) {
  const [user, setUser] = useState<User | null>(null);
  const [token, setToken] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    // Check for existing token on mount
    const storedToken = localStorage.getItem('token');
    if (storedToken) {
      setToken(storedToken);
      fetchCurrentUser(storedToken);
    } else {
      setLoading(false);
    }
  }, []);

  const fetchCurrentUser = async (authToken: string) => {
    try {
      const response = await fetch('/api/auth/me', {
        headers: {
          'Authorization': `Bearer ${authToken}`,
        },
      });

      if (response.ok) {
        const userData = await response.json();
        setUser(userData);
      } else {
        // Token is invalid, clear it
        localStorage.removeItem('token');
        setToken(null);
        // Redirect to signin if token is invalid
        if (typeof window !== 'undefined') {
          window.location.href = '/signin';
        }
      }
    } catch (error) {
      console.error('Error fetching current user:', error);
      localStorage.removeItem('token');
      setToken(null);
      // Redirect to signin on network errors with token
      if (typeof window !== 'undefined') {
        window.location.href = '/signin';
      }
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

      const response = await fetch('/api/auth/login', {
        method: 'POST',
        body: formData,
      });

      if (response.ok) {
        const data = await response.json();
        const { access_token } = data;

        setToken(access_token);
        localStorage.setItem('token', access_token);

        // Fetch user data
        await fetchCurrentUser(access_token);
        return true;
      } else {
        const errorData = await response.json();
        setError(parseApiError(errorData));
        return false;
      }
    } catch (error) {
      setError('Network error. Please try again.');
      return false;
    } finally {
      setLoading(false);
    }
  };

  const register = async (username: string, email: string, password: string): Promise<boolean> => {
    setLoading(true);
    setError(null);

    try {
      const response = await fetch('/api/auth/register', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          username,
          email,
          password,
        }),
      });

      if (response.ok) {
        // Auto-login after successful registration
        return await login(username, password);
      } else {
        const errorData = await response.json();
        setError(parseApiError(errorData));
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
    setUser(null);
    setToken(null);
    localStorage.removeItem('token');
    // Redirect to signin page
    if (typeof window !== 'undefined') {
      window.location.href = '/signin';
    }
  };

  const value: AuthContextType = {
    user,
    token,
    login,
    register,
    logout,
    loading,
    error,
  };

  return (
    <AuthContext.Provider value={value}>
      {children}
    </AuthContext.Provider>
  );
}
