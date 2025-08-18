'use client';

import { useState } from 'react';
import { X } from 'lucide-react';

interface CreateLeagueModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSubmit: (data: { name: string; description?: string; max_teams: number }) => Promise<void>;
}

export default function CreateLeagueModal({ isOpen, onClose, onSubmit }: CreateLeagueModalProps) {
  const [name, setName] = useState('');
  const [description, setDescription] = useState('');
  const [maxTeams, setMaxTeams] = useState(8);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  if (!isOpen) return null;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!name.trim()) {
      setError('Please enter a league name');
      return;
    }
    try {
      setSubmitting(true);
      setError(null);
      await onSubmit({ name: name.trim(), description: description.trim() || undefined, max_teams: maxTeams });
      // Reset form on success
      setName('');
      setDescription('');
      setMaxTeams(8);
      onClose();
    } catch (err: any) {
      setError(err?.message || 'Failed to create league');
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
      <div className="bg-white rounded-lg p-6 w-full max-w-md mx-4">
        <div className="flex justify-between items-center mb-4">
          <h2 className="text-xl font-semibold">Create a League</h2>
          <button onClick={onClose} className="text-gray-400 hover:text-gray-600">
            <X className="h-5 w-5" />
          </button>
        </div>

        {error && (
          <div className="mb-4 p-3 bg-red-50 border border-red-200 text-red-700 rounded">
            {error}
          </div>
        )}

        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">League Name</label>
            <input
              type="text"
              value={name}
              onChange={(e) => setName(e.target.value)}
              className="input-field"
              placeholder="Enter league name"
              required
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Description (optional)</label>
            <input
              type="text"
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              className="input-field"
              placeholder="Add a short description"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Max Teams</label>
            <select
              value={maxTeams}
              onChange={(e) => setMaxTeams(Number(e.target.value))}
              className="input-field"
            >
              {[4, 6, 8, 10, 12].map((v) => (
                <option key={v} value={v}>{v}</option>
              ))}
            </select>
          </div>

          <button
            type="submit"
            disabled={submitting || !name.trim()}
            className="w-full btn-primary disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {submitting ? 'Creating...' : 'Create League'}
          </button>
        </form>
      </div>
    </div>
  );
}


