'use client';

import { useEffect, ReactNode } from 'react';
import { createPortal } from 'react-dom';
import { X } from 'lucide-react';

interface SidePanelProps {
    isOpen: boolean;
    onClose: () => void;
    title: string;
    children: ReactNode;
    footer?: ReactNode;
}

export default function SidePanel({ isOpen, onClose, title, children, footer }: SidePanelProps) {
    // Prevent body scroll when panel is open
    useEffect(() => {
        if (isOpen) {
            document.body.style.overflow = 'hidden';
        } else {
            document.body.style.overflow = '';
        }
        return () => {
            document.body.style.overflow = '';
        };
    }, [isOpen]);

    // Handle escape key to close
    useEffect(() => {
        const handleEscape = (e: KeyboardEvent) => {
            if (e.key === 'Escape' && isOpen) {
                onClose();
            }
        };
        document.addEventListener('keydown', handleEscape);
        return () => document.removeEventListener('keydown', handleEscape);
    }, [isOpen, onClose]);

    // Only render in browser (not during SSR)
    if (typeof document === 'undefined') {
        return null;
    }

    return createPortal(
        <div
            className={`fixed inset-0 z-[9999] transition-opacity duration-300 ${isOpen ? 'opacity-100 pointer-events-auto' : 'opacity-0 pointer-events-none'}`}
        >
            {/* Faded backdrop */}
            <div
                className="absolute inset-0 bg-black/60"
                onClick={onClose}
            />
            {/* Side panel sliding in from right */}
            <div
                className={`absolute top-0 right-0 h-full w-full max-w-md border-l border-gray-600 shadow-2xl transition-transform duration-300 ease-out ${isOpen ? 'translate-x-0' : 'translate-x-full'}`}
                style={{ backgroundColor: 'rgb(20, 29, 38)' }}
            >
                <div className="flex flex-col h-full p-6">
                    {/* Header */}
                    <div className="flex items-center justify-between mb-6">
                        <h3 className="text-xl font-semibold text-white">{title}</h3>
                        <button
                            onClick={onClose}
                            className="p-2 text-gray-400 hover:text-white hover:bg-white/10 rounded-lg transition-colors"
                        >
                            <X className="h-5 w-5" />
                        </button>
                    </div>

                    {/* Content */}
                    <div className="flex-1 overflow-y-auto">
                        {children}
                    </div>

                    {/* Footer (optional) */}
                    {footer && (
                        <div className="mt-6 pt-4 border-t border-gray-600">
                            {footer}
                        </div>
                    )}
                </div>
            </div>
        </div>,
        document.body
    );
}
