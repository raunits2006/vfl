'use client';

import React, { createContext, useContext, useState, ReactNode, useCallback } from 'react';

type ToastType = 'success' | 'error' | 'info' | 'warning';

export interface ToastItem {
  id: string;
  type: ToastType;
  title?: string;
  message: string;
  timeoutMs?: number;
}

interface ToastContextValue {
  showToast: (message: string, opts?: { type?: ToastType; title?: string; timeoutMs?: number }) => void;
}

const ToastContext = createContext<ToastContextValue | undefined>(undefined);

export function useToast() {
  const ctx = useContext(ToastContext);
  if (!ctx) throw new Error('useToast must be used within ToastProvider');
  return ctx;
}

export default function ToastProvider({ children }: { children: ReactNode }) {
  const [toasts, setToasts] = useState<ToastItem[]>([]);

  const remove = useCallback((id: string) => {
    setToasts(prev => prev.filter(t => t.id !== id));
  }, []);

  const showToast = useCallback((message: string, opts?: { type?: ToastType; title?: string; timeoutMs?: number }) => {
    const id = Math.random().toString(36).slice(2);
    const toast: ToastItem = {
      id,
      type: opts?.type || 'info',
      title: opts?.title,
      message,
      timeoutMs: opts?.timeoutMs ?? 3500,
    };
    setToasts(prev => [...prev, toast]);
    if (toast.timeoutMs && toast.timeoutMs > 0) {
      setTimeout(() => remove(id), toast.timeoutMs);
    }
  }, [remove]);

  return (
    <ToastContext.Provider value={{ showToast }}>
      {children}
      {/* Container */}
      <div className="fixed inset-0 pointer-events-none flex flex-col items-end gap-2 p-4 sm:p-6 z-[9999]">
        {toasts.map(t => (
          <div
            key={t.id}
            className={`pointer-events-auto w-full sm:w-auto max-w-sm rounded-md shadow-lg border text-sm p-3 sm:p-4 bg-white ${
              t.type === 'success' ? 'border-green-200' : t.type === 'error' ? 'border-red-200' : t.type === 'warning' ? 'border-yellow-200' : 'border-gray-200'
            }`}
          >
            {t.title && <div className="font-semibold mb-1">{t.title}</div>}
            <div className="text-gray-700">{t.message}</div>
            <div className="mt-2 flex justify-end">
              <button onClick={() => remove(t.id)} className="px-2 py-1 rounded text-xs bg-gray-100 hover:bg-gray-200 text-gray-700">Dismiss</button>
            </div>
          </div>
        ))}
      </div>
    </ToastContext.Provider>
  );
}


