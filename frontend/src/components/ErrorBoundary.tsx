'use client';

import React, { Component, ErrorInfo, ReactNode } from 'react';

interface Props {
    children: ReactNode;
}

interface State {
    hasError: boolean;
    error: Error | null;
}

/**
 * Global Error Boundary component to catch unhandled React rendering errors.
 * Prevents the entire app from crashing and shows a user-friendly error message.
 */
class ErrorBoundary extends Component<Props, State> {
    constructor(props: Props) {
        super(props);
        this.state = { hasError: false, error: null };
    }

    static getDerivedStateFromError(error: Error): State {
        return { hasError: true, error };
    }

    componentDidCatch(error: Error, errorInfo: ErrorInfo) {
        // Log error to console in development
        console.error('ErrorBoundary caught an error:', error, errorInfo);
    }

    handleRefresh = () => {
        window.location.reload();
    };

    handleGoHome = () => {
        window.location.href = '/';
    };

    render() {
        if (this.state.hasError) {
            return (
                <div className="min-h-screen bg-gradient-to-br from-valorant-900 via-valorant-800 to-valorant-700 flex items-center justify-center py-12 px-4">
                    <div className="max-w-md w-full bg-white rounded-lg shadow-xl p-8 text-center">
                        <div className="mx-auto h-16 w-16 bg-red-100 rounded-full flex items-center justify-center mb-6">
                            <svg
                                className="h-8 w-8 text-red-600"
                                fill="none"
                                viewBox="0 0 24 24"
                                stroke="currentColor"
                            >
                                <path
                                    strokeLinecap="round"
                                    strokeLinejoin="round"
                                    strokeWidth={2}
                                    d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"
                                />
                            </svg>
                        </div>

                        <h2 className="text-2xl font-bold text-gray-900 mb-2">
                            Something went wrong
                        </h2>

                        <p className="text-gray-600 mb-6">
                            We&apos;re sorry, but something unexpected happened. Please try refreshing the page or go back to the home page.
                        </p>

                        <div className="space-y-3">
                            <button
                                onClick={this.handleRefresh}
                                className="w-full bg-valorant-600 hover:bg-valorant-700 text-white font-medium py-3 px-4 rounded-lg transition-colors duration-200"
                            >
                                Refresh Page
                            </button>

                            <button
                                onClick={this.handleGoHome}
                                className="w-full bg-gray-100 hover:bg-gray-200 text-gray-700 font-medium py-3 px-4 rounded-lg transition-colors duration-200"
                            >
                                Go to Home Page
                            </button>
                        </div>

                        {process.env.NODE_ENV === 'development' && this.state.error && (
                            <div className="mt-6 p-4 bg-gray-100 rounded-lg text-left">
                                <p className="text-xs font-mono text-red-600 break-all">
                                    {this.state.error.toString()}
                                </p>
                            </div>
                        )}
                    </div>
                </div>
            );
        }

        return this.props.children;
    }
}

export default ErrorBoundary;
