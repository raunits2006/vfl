'use client';

import { useEffect, useMemo, useState } from 'react';
import { ChevronUp, ChevronDown, Shuffle, X } from 'lucide-react';

export interface DraftMember {
  user_id: number;
  username: string;
}

interface SetDraftOrderModalProps {
  isOpen: boolean;
  onClose: () => void;
  members: DraftMember[];
  onSubmit: (orderedUserIds: number[]) => Promise<void>;
}

export default function SetDraftOrderModal({ isOpen, onClose, members, onSubmit }: SetDraftOrderModalProps) {
  const [order, setOrder] = useState<DraftMember[]>([]);
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    if (isOpen) {
      setOrder(members);
    }
  }, [isOpen, members]);

  const moveUp = (index: number) => {
    if (index <= 0) return;
    setOrder(prev => {
      const next = [...prev];
      [next[index - 1], next[index]] = [next[index], next[index - 1]];
      return next;
    });
  };

  const moveDown = (index: number) => {
    setOrder(prev => {
      if (index >= prev.length - 1) return prev;
      const next = [...prev];
      [next[index + 1], next[index]] = [next[index], next[index + 1]];
      return next;
    });
  };

  const randomize = () => {
    setOrder(prev => {
      const next = [...prev];
      for (let i = next.length - 1; i > 0; i--) {
        const j = Math.floor(Math.random() * (i + 1));
        [next[i], next[j]] = [next[j], next[i]];
      }
      return next;
    });
  };

  const handleSubmit = async () => {
    try {
      setSubmitting(true);
      await onSubmit(order.map(m => m.user_id));
    } finally {
      setSubmitting(false);
    }
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 z-50 flex items-center justify-center">
      <div className="bg-white rounded-lg shadow-xl w-full max-w-lg mx-4">
        <div className="flex items-center justify-between p-4 border-b">
          <h2 className="text-lg font-semibold">Set Draft Order</h2>
          <button onClick={onClose} className="text-gray-500 hover:text-gray-700">
            <X className="h-5 w-5" />
          </button>
        </div>

        <div className="p-4 space-y-3 max-h-[60vh] overflow-y-auto">
          {order.length === 0 && (
            <p className="text-sm text-gray-600">No members to order.</p>
          )}
          {order.map((m, idx) => (
            <div key={m.user_id} className="flex items-center justify-between p-2 border rounded">
              <div className="flex items-center space-x-3">
                <span className="w-6 text-right font-medium">{idx + 1}</span>
                <span className="font-medium">{m.username}</span>
              </div>
              <div className="flex items-center space-x-2">
                <button onClick={() => moveUp(idx)} className="btn-secondary px-2 py-1"><ChevronUp className="h-4 w-4"/></button>
                <button onClick={() => moveDown(idx)} className="btn-secondary px-2 py-1"><ChevronDown className="h-4 w-4"/></button>
              </div>
            </div>
          ))}
        </div>

        <div className="p-4 border-t flex items-center justify-between">
          <button onClick={randomize} className="btn-secondary flex items-center">
            <Shuffle className="h-4 w-4 mr-2"/> Randomize
          </button>
          <div className="space-x-2">
            <button onClick={onClose} className="btn-secondary">Cancel</button>
            <button onClick={handleSubmit} disabled={submitting || order.length === 0} className="btn-primary">
              {submitting ? 'Saving...' : 'Save Order'}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}


