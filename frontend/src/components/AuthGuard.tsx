'use client';

import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import { useAuth } from '../contexts/AuthContext';

/**
 * AuthGuard — wraps protected routes and redirects unauthenticated users
 * to /signin. Shows a loading spinner while checking auth state.
 *
 * Usage:
 *   <AuthGuard>
 *     <YourProtectedPage />
 *   </AuthGuard>
 */
export default function AuthGuard({ children }: { children: React.ReactNode }) {
  const { user, token, loading: authLoading } = useAuth();
  const router = useRouter();
  const [checked, setChecked] = useState(false);

  useEffect(() => {
    if (!authLoading) {
      if (!token || !user) {
        sessionStorage.setItem('redirectAfterLogin', window.location.pathname);
        router.replace('/signin');
      }
      setChecked(true);
    }
  }, [authLoading, token, user, router]);

  if (authLoading || !checked) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-50">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-valorant-600 mx-auto" />
          <p className="mt-4 text-gray-600 text-sm">Checking authentication…</p>
        </div>
      </div>
    );
  }

  if (!token || !user) {
    return null; // router.replace is in-flight
  }

  return <>{children}</>;
}