/**
 * Global Error Boundary Component
 * ================================
 * Catches React rendering errors and provides fallback UI.
 * Prevents entire app from crashing due to component errors.
 */

import React, { Component, ErrorInfo, ReactNode } from 'react';

interface ErrorBoundaryProps {
    children: ReactNode;
    fallback?: ReactNode;
}

interface ErrorBoundaryState {
    hasError: boolean;
    error: Error | null;
    errorInfo: ErrorInfo | null;
}

export class ErrorBoundary extends Component<ErrorBoundaryProps, ErrorBoundaryState> {
    constructor(props: ErrorBoundaryProps) {
        super(props);
        this.state = {
            hasError: false,
            error: null,
            errorInfo: null,
        };
    }

    static getDerivedStateFromError(error: Error): Partial<ErrorBoundaryState> {
        return { hasError: true, error };
    }

    componentDidCatch(error: Error, errorInfo: ErrorInfo): void {
        console.error('ErrorBoundary caught an error:', error, errorInfo);
        this.setState({ errorInfo });

        if (import.meta.env.PROD) {
            this.logErrorToBackend(error, errorInfo);
        }
    }

    private logErrorToBackend(error: Error, errorInfo: ErrorInfo): void {
        fetch('/api/v1/errors', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                error: error.message,
                stack: error.stack,
                componentStack: errorInfo.componentStack,
                timestamp: new Date().toISOString(),
            }),
        }).catch(console.error);
    }

    private handleReset = (): void => {
        this.setState({ hasError: false, error: null, errorInfo: null });
    };

    render(): ReactNode {
        if (this.state.hasError) {
            if (this.props.fallback) {
                return this.props.fallback;
            }

            return (
                <div className="min-h-screen flex items-center justify-center bg-slate-900 p-6">
                    <div className="max-w-lg w-full bg-slate-800 rounded-xl p-8 shadow-xl border border-red-500/20">
                        <div className="text-center mb-6">
                            <span className="text-5xl">⚠️</span>
                            <h1 className="text-2xl font-bold text-white mt-4">Something went wrong</h1>
                            <p className="text-slate-400 mt-2">
                                An unexpected error occurred. Please try refreshing the page.
                            </p>
                        </div>

                        {import.meta.env.DEV && this.state.error && (
                            <div className="mt-6 p-4 bg-red-900/20 rounded-lg border border-red-500/30">
                                <h3 className="text-red-400 font-semibold text-sm mb-2">Error Details (Dev Only)</h3>
                                <pre className="text-xs text-red-300 overflow-auto max-h-40">
                                    {this.state.error.message}
                                    {'\n\n'}
                                    {this.state.error.stack}
                                </pre>
                            </div>
                        )}

                        <div className="mt-6 flex gap-4">
                            <button
                                onClick={this.handleReset}
                                className="flex-1 px-4 py-3 bg-indigo-600 text-white rounded-lg font-medium hover:bg-indigo-700 transition-colors"
                            >
                                Try Again
                            </button>
                            <button
                                onClick={() => window.location.reload()}
                                className="flex-1 px-4 py-3 bg-slate-700 text-white rounded-lg font-medium hover:bg-slate-600 transition-colors"
                            >
                                Refresh Page
                            </button>
                        </div>
                    </div>
                </div>
            );
        }

        return this.props.children;
    }
}

export default ErrorBoundary;
