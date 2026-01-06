'use client';

import { ReactNode } from 'react';
import Navbar from './Navbar';
import { AuthProvider } from '../contexts/AuthContext';
import ToastProvider from './ToastProvider';
import ErrorBoundary from './ErrorBoundary';

interface ClientLayoutProps {
  children: ReactNode;
}

export default function ClientLayout({ children }: ClientLayoutProps) {
  return (
    <ErrorBoundary>
      <AuthProvider>
        <ToastProvider>
          <div className="min-h-screen bg-gray-50">
            <Navbar />
            <main className="max-w-7xl mx-auto py-6 sm:px-6 lg:px-8">
              {children}
            </main>
          </div>
        </ToastProvider>
      </AuthProvider>
    </ErrorBoundary>
  );
}
