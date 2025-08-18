'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import { Eye, EyeOff, Shield, Lock, User } from 'lucide-react';
import { useAdminAuth } from '../../../contexts/AdminAuthContext';

export default function AdminLoginPage() {
  const router = useRouter();
  const { login, loading, error } = useAdminAuth();
  const [showPassword, setShowPassword] = useState(false);
  const [formData, setFormData] = useState({
    username: '',
    password: '',
  });

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    const success = await login(formData.username, formData.password);
    if (success) {
      router.push('/admin/dashboard');
    }
  };

  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    setFormData({
      ...formData,
      [e.target.name]: e.target.value,
    });
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-red-900 via-red-800 to-red-700 flex items-center justify-center py-12 px-4 sm:px-6 lg:px-8">
      <div className="max-w-md w-full space-y-8">
        <div className="text-center">
          <div className="mx-auto h-16 w-16 bg-red-600 rounded-full flex items-center justify-center mb-4">
            <Shield className="h-8 w-8 text-white" />
          </div>
          <h2 className="text-3xl font-bold text-white mb-2">
            Admin Access
          </h2>
          <p className="text-red-200">
            Authorized personnel only
          </p>
        </div>

        <div className="bg-white/10 backdrop-blur-sm rounded-xl shadow-2xl p-8 border border-white/20">
          <form className="space-y-6" onSubmit={handleSubmit}>
            {error && (
              <div className="bg-red-500/20 border border-red-500 text-red-100 px-4 py-3 rounded-lg">
                {error}
              </div>
            )}

            <div>
              <label htmlFor="username" className="block text-sm font-medium text-white mb-2">
                Admin Username
              </label>
              <div className="relative">
                <div className="absolute inset-y-0 left-0 pl-3 flex items-center">
                  <User className="h-5 w-5 text-red-300" />
                </div>
                <input
                  id="username"
                  name="username"
                  type="text"
                  required
                  value={formData.username}
                  onChange={handleInputChange}
                  className="block w-full pl-10 pr-3 py-3 border border-white/30 rounded-lg bg-white/10 backdrop-blur-sm text-white placeholder-red-200 focus:outline-none focus:ring-2 focus:ring-red-400 focus:border-transparent"
                  placeholder="Enter admin username"
                />
              </div>
            </div>

            <div>
              <label htmlFor="password" className="block text-sm font-medium text-white mb-2">
                Password
              </label>
              <div className="relative">
                <div className="absolute inset-y-0 left-0 pl-3 flex items-center">
                  <Lock className="h-5 w-5 text-red-300" />
                </div>
                <input
                  id="password"
                  name="password"
                  type={showPassword ? 'text' : 'password'}
                  required
                  value={formData.password}
                  onChange={handleInputChange}
                  className="block w-full pl-10 pr-12 py-3 border border-white/30 rounded-lg bg-white/10 backdrop-blur-sm text-white placeholder-red-200 focus:outline-none focus:ring-2 focus:ring-red-400 focus:border-transparent"
                  placeholder="Enter admin password"
                />
                <button
                  type="button"
                  className="absolute inset-y-0 right-0 pr-3 flex items-center"
                  onClick={() => setShowPassword(!showPassword)}
                >
                  {showPassword ? (
                    <EyeOff className="h-5 w-5 text-red-300 hover:text-white" />
                  ) : (
                    <Eye className="h-5 w-5 text-red-300 hover:text-white" />
                  )}
                </button>
              </div>
            </div>

            <div>
              <button
                type="submit"
                disabled={loading}
                className="group relative w-full flex justify-center py-3 px-4 border border-transparent text-sm font-medium rounded-lg text-white bg-red-600 hover:bg-red-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-red-500 disabled:opacity-50 disabled:cursor-not-allowed transition-colors duration-200"
              >
                {loading ? (
                  <div className="flex items-center">
                    <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white mr-2"></div>
                    Authenticating...
                  </div>
                ) : (
                  <div className="flex items-center">
                    <Shield className="h-4 w-4 mr-2" />
                    Access Admin Panel
                  </div>
                )}
              </button>
            </div>
          </form>

          <div className="mt-6 text-center">
            <p className="text-red-200 text-sm">
              This area is restricted to authorized administrators only.
              <br />
              Unauthorized access attempts are logged and monitored.
            </p>
          </div>
        </div>

        <div className="text-center">
          <a
            href="/"
            className="text-red-200 hover:text-white text-sm transition-colors duration-200"
          >
            ← Return to main site
          </a>
        </div>
      </div>
    </div>
  );
}
