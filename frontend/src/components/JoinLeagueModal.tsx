'use client';

import { useState } from 'react';
import { X } from 'lucide-react';

interface JoinLeagueModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSubmit: (pin: string) => Promise<void>;
}

export default function JoinLeagueModal({ isOpen, onClose, onSubmit }: JoinLeagueModalProps) {
  const [pin, setPin] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  if (!isOpen) return null;

  const handleSubmit = async () => {
    if (pin.length !== 6 || !/^\d{6}$/.test(pin)) {
      setError('Please enter a valid 6-digit PIN');
      return;
    }
    try {
      setSubmitting(true);
      setError(null);
      await onSubmit(pin);
      setPin('');
      onClose();
    } catch (err: any) {
      setError(err?.message || 'Failed to join league');
    } finally {
      setSubmitting(false);
    }
  };

  const handleChange = (value: string) => {
    // Only allow digits, max length 6
    const cleaned = value.replace(/\D/g, '').slice(0, 6);
    setPin(cleaned);
    if (error) setError(null);
  };

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
      <div className="bg-white rounded-lg p-6 w-full max-w-sm mx-4">
        <div className="flex justify-between items-center mb-4">
          <h2 className="text-xl font-semibold">Join a League</h2>
          <button onClick={onClose} className="text-gray-400 hover:text-gray-600">
            <X className="h-5 w-5" />
          </button>
        </div>

        {error && (
          <div className="mb-4 p-3 bg-red-50 border border-red-200 text-red-700 rounded">
            {error}
          </div>
        )}

        <div className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">6-digit PIN</label>
            <input
              type="text"
              inputMode="numeric"
              value={pin}
              onChange={(e) => handleChange(e.target.value)}
              className="input-field text-center tracking-widest text-lg"
              placeholder="000000"
              maxLength={6}
            />
            <p className="mt-1 text-xs text-gray-500 text-center">Ask your commissioner for the league PIN</p>
          </div>

          <button
            type="button"
            onClick={handleSubmit}
            disabled={submitting || pin.length !== 6}
            className="w-full btn-primary disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {submitting ? 'Joining...' : 'Join League'}
          </button>
        </div>
      </div>
    </div>
  );
}


