'use client';

import { useState } from 'react';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { Eye, EyeOff, LogIn, ArrowLeft } from 'lucide-react';
import { useAuth } from '../../contexts/AuthContext';

export default function SignInPage() {
  const router = useRouter();
  const { login, loading, error } = useAuth();
  const [showPassword, setShowPassword] = useState(false);
  const [formData, setFormData] = useState({
    username: '',
    password: '',
  });

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    const success = await login(formData.username, formData.password);
    if (success) {
      router.push('/leagues');
    }
  };

  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    setFormData({
      ...formData,
      [e.target.name]: e.target.value,
    });
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-valorant-900 via-valorant-800 to-valorant-700 flex items-center justify-center py-12 px-4 sm:px-6 lg:px-8">
      <div className="max-w-md w-full space-y-8">
        {/* Back to Home Link */}
        <div>
          <Link 
            href="/" 
            className="inline-flex items-center text-valorant-200 hover:text-white transition-colors duration-200"
          >
            <ArrowLeft className="h-4 w-4 mr-2" />
            Back to Home
          </Link>
        </div>

        {/* Header */}
        <div className="text-center">
          <div className="mx-auto h-12 w-12 bg-white rounded-full flex items-center justify-center mb-4">
            <LogIn className="h-6 w-6 text-valorant-600" />
          </div>
          <h2 className="text-3xl font-bold text-white">
            Welcome Back
          </h2>
          <p className="mt-2 text-sm text-valorant-200">
            Sign in to your Valorant Fantasy League account
          </p>
        </div>

        {/* Sign In Form */}
        <div className="bg-white rounded-lg shadow-xl p-8">
          {error && (
            <div className="mb-6 p-4 bg-red-50 border border-red-200 text-red-700 rounded-lg">
              {error}
            </div>
          )}

          <form onSubmit={handleSubmit} className="space-y-6">
            <div>
              <label htmlFor="username" className="block text-sm font-medium text-gray-700 mb-2">
                Username
              </label>
              <input
                type="text"
                id="username"
                name="username"
                value={formData.username}
                onChange={handleInputChange}
                className="input-field"
                placeholder="Enter your username"
                required
              />
            </div>

            <div>
              <label htmlFor="password" className="block text-sm font-medium text-gray-700 mb-2">
                Password
              </label>
              <div className="relative">
                <input
                  type={showPassword ? 'text' : 'password'}
                  id="password"
                  name="password"
                  value={formData.password}
                  onChange={handleInputChange}
                  className="input-field pr-10"
                  placeholder="Enter your password"
                  required
                />
                <button
                  type="button"
                  onClick={() => setShowPassword(!showPassword)}
                  className="absolute inset-y-0 right-0 pr-3 flex items-center text-gray-400 hover:text-gray-600"
                >
                  {showPassword ? (
                    <EyeOff className="h-5 w-5" />
                  ) : (
                    <Eye className="h-5 w-5" />
                  )}
                </button>
              </div>
            </div>

            <div>
              <button
                type="submit"
                disabled={loading}
                className="w-full btn-primary py-3 text-lg font-medium disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {loading ? (
                  <div className="flex items-center justify-center">
                    <div className="animate-spin rounded-full h-5 w-5 border-b-2 border-white mr-2"></div>
                    Signing In...
                  </div>
                ) : (
                  'Sign In'
                )}
              </button>
            </div>
          </form>

          {/* Sign Up Link */}
          <div className="mt-6 text-center">
            <p className="text-sm text-gray-600">
              Don&apos;t have an account?{' '}
              <Link 
                href="/signup" 
                className="font-medium text-valorant-600 hover:text-valorant-500 transition-colors duration-200"
              >
                Create one now
              </Link>
            </p>
          </div>
        </div>

        {/* Features Preview */}
        <div className="text-center">
          <p className="text-sm text-valorant-200 mb-4">
            Join thousands of Valorant fans competing in fantasy leagues
          </p>
          <div className="flex justify-center space-x-6 text-xs text-valorant-300">
            <span>• Live Scoring</span>
            <span>• Real-time Drafts</span>
            <span>• Competitive Leagues</span>
          </div>
        </div>
      </div>
    </div>
  );
}
