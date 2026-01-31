// Error Boundary Component for Graceful Degradation
// ========================================
import { Component, type ReactNode } from 'react';

interface Props {
    children: ReactNode;
    fallback?: ReactNode;
}

interface State {
    hasError: boolean;
    error: Error | null;
}

export class ErrorBoundary extends Component<Props, State> {
    constructor(props: Props) {
        super(props);
        this.state = { hasError: false, error: null };
    }

    static getDerivedStateFromError(error: Error): State {
        return { hasError: true, error };
    }

    componentDidCatch(error: Error, errorInfo: React.ErrorInfo) {
        console.error('ErrorBoundary caught an error:', error, errorInfo);
    }

    render() {
        if (this.state.hasError) {
            if (this.props.fallback) {
                return this.props.fallback;
            }

            return (
                <div className="min-h-[400px] flex items-center justify-center">
                    <div className="text-center p-8 bg-white dark:bg-slate-800 rounded-xl shadow-sm border border-slate-200 dark:border-slate-700 max-w-md">
                        <div className="text-5xl mb-4">⚠️</div>
                        <h2 className="text-xl font-semibold text-slate-900 dark:text-white mb-2">
                            Something went wrong
                        </h2>
                        <p className="text-slate-500 dark:text-slate-400 mb-4">
                            We encountered an unexpected error. Please try refreshing the page.
                        </p>
                        <button
                            onClick={() => window.location.reload()}
                            className="px-4 py-2 bg-indigo-600 text-white rounded-lg hover:bg-indigo-700 transition-colors"
                        >
                            Refresh Page
                        </button>
                        {this.state.error && (
                            <details className="mt-4 text-left">
                                <summary className="text-sm text-slate-500 cursor-pointer">Error details</summary>
                                <pre className="mt-2 p-2 bg-slate-100 dark:bg-slate-900 rounded text-xs overflow-auto">
                                    {this.state.error.message}
                                </pre>
                            </details>
                        )}
                    </div>
                </div>
            );
        }

        return this.props.children;
    }
}

export default ErrorBoundary;
