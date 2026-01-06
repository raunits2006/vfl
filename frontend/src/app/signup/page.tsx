'use client';

import { useState } from 'react';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { Eye, EyeOff, UserPlus, ArrowLeft, Check } from 'lucide-react';
import { useAuth } from '../../contexts/AuthContext';
import { useToast } from '../../components/ToastProvider';

export default function SignUpPage() {
  const router = useRouter();
  const { register, loading, error } = useAuth();
  const { showToast } = useToast();
  const [showPassword, setShowPassword] = useState(false);
  const [showConfirmPassword, setShowConfirmPassword] = useState(false);
  const [formData, setFormData] = useState({
    username: '',
    email: '',
    password: '',
    confirmPassword: '',
  });
  const [passwordErrors, setPasswordErrors] = useState<string[]>([]);

  const validatePassword = (password: string): string[] => {
    const errors: string[] = [];
    if (password.length < 8) errors.push('At least 8 characters');
    if (!/[A-Z]/.test(password)) errors.push('One uppercase letter');
    if (!/[a-z]/.test(password)) errors.push('One lowercase letter');
    if (!/[0-9]/.test(password)) errors.push('One number');
    if (!/[!@#$%^&*(),.?":{}|<>]/.test(password)) errors.push('One special character');
    return errors;
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    if (formData.password !== formData.confirmPassword) {
      showToast('Passwords do not match', { type: 'warning' });
      return;
    }

    const errors = validatePassword(formData.password);
    if (errors.length > 0) {
      showToast('Password does not meet requirements', { type: 'warning' });
      return;
    }

    const success = await register(formData.username, formData.email, formData.password);
    if (success) {
      showToast('Account created successfully', { type: 'success' });
      router.push('/leagues');
    }
  };

  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const { name, value } = e.target;
    setFormData({
      ...formData,
      [name]: value,
    });

    if (name === 'password') {
      setPasswordErrors(validatePassword(value));
    }
  };

  const isPasswordValid = passwordErrors.length === 0 && formData.password.length > 0;
  const passwordsMatch = formData.password === formData.confirmPassword && formData.confirmPassword.length > 0;

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
            <UserPlus className="h-6 w-6 text-valorant-600" />
          </div>
          <h2 className="text-3xl font-bold text-white">
            Join the League
          </h2>
          <p className="mt-2 text-sm text-valorant-200">
            Create your account and start competing in Valorant fantasy leagues
          </p>
        </div>

        {/* Sign Up Form */}
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
                placeholder="Choose a unique username"
                required
              />
            </div>

            <div>
              <label htmlFor="email" className="block text-sm font-medium text-gray-700 mb-2">
                Email Address
              </label>
              <input
                type="email"
                id="email"
                name="email"
                value={formData.email}
                onChange={handleInputChange}
                className="input-field"
                placeholder="your.email@example.com"
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
                  className={`input-field pr-10 ${formData.password && !isPasswordValid ? 'border-red-300' : formData.password && isPasswordValid ? 'border-green-300' : ''}`}
                  placeholder="Create a strong password"
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

              {/* Password Requirements */}
              {formData.password && (
                <div className="mt-2 space-y-1">
                  <p className="text-xs text-gray-600">Password requirements:</p>
                  {['At least 8 characters', 'One uppercase letter', 'One lowercase letter', 'One number', 'One special character'].map((requirement) => {
                    const isMet = !passwordErrors.includes(requirement);
                    return (
                      <div key={requirement} className={`flex items-center text-xs ${isMet ? 'text-green-600' : 'text-gray-400'}`}>
                        <Check className={`h-3 w-3 mr-1 ${isMet ? 'text-green-600' : 'text-gray-300'}`} />
                        {requirement}
                      </div>
                    );
                  })}
                </div>
              )}
            </div>

            <div>
              <label htmlFor="confirmPassword" className="block text-sm font-medium text-gray-700 mb-2">
                Confirm Password
              </label>
              <div className="relative">
                <input
                  type={showConfirmPassword ? 'text' : 'password'}
                  id="confirmPassword"
                  name="confirmPassword"
                  value={formData.confirmPassword}
                  onChange={handleInputChange}
                  className={`input-field pr-10 ${formData.confirmPassword && !passwordsMatch ? 'border-red-300' : formData.confirmPassword && passwordsMatch ? 'border-green-300' : ''}`}
                  placeholder="Confirm your password"
                  required
                />
                <button
                  type="button"
                  onClick={() => setShowConfirmPassword(!showConfirmPassword)}
                  className="absolute inset-y-0 right-0 pr-3 flex items-center text-gray-400 hover:text-gray-600"
                >
                  {showConfirmPassword ? (
                    <EyeOff className="h-5 w-5" />
                  ) : (
                    <Eye className="h-5 w-5" />
                  )}
                </button>
              </div>
              {formData.confirmPassword && !passwordsMatch && (
                <p className="mt-1 text-xs text-red-600">Passwords do not match</p>
              )}
              {formData.confirmPassword && passwordsMatch && (
                <p className="mt-1 text-xs text-green-600 flex items-center">
                  <Check className="h-3 w-3 mr-1" />
                  Passwords match
                </p>
              )}
            </div>

            <div>
              <button
                type="submit"
                disabled={loading || !isPasswordValid || !passwordsMatch}
                className="w-full btn-primary py-3 text-lg font-medium disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {loading ? (
                  <div className="flex items-center justify-center">
                    <div className="animate-spin rounded-full h-5 w-5 border-b-2 border-white mr-2"></div>
                    Creating Account...
                  </div>
                ) : (
                  'Create Account'
                )}
              </button>
            </div>
          </form>

          {/* Sign In Link */}
          <div className="mt-6 text-center">
            <p className="text-sm text-gray-600">
              Already have an account?{' '}
              <Link
                href="/signin"
                className="font-medium text-valorant-600 hover:text-valorant-500 transition-colors duration-200"
              >
                Sign in here
              </Link>
            </p>
          </div>
        </div>

        {/* Benefits */}
        <div className="bg-white bg-opacity-10 rounded-lg p-6">
          <h3 className="text-white font-medium mb-3">What you get:</h3>
          <ul className="space-y-2 text-sm text-valorant-200">
            <li className="flex items-center">
              <Check className="h-4 w-4 mr-2 text-green-400" />
              Draft your favorite Valorant pros
            </li>
            <li className="flex items-center">
              <Check className="h-4 w-4 mr-2 text-green-400" />
              Compete with friends in private leagues
            </li>
            <li className="flex items-center">
              <Check className="h-4 w-4 mr-2 text-green-400" />
              Real-time scoring from VCT matches
            </li>
            <li className="flex items-center">
              <Check className="h-4 w-4 mr-2 text-green-400" />
              Trade players and manage lineups
            </li>
          </ul>
        </div>
      </div>
    </div>
  );
}
