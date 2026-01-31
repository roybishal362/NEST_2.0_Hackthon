/**
 * Toast Notification System
 * ==========================
 * Provides user-friendly notifications for success, error, warning, and info messages.
 * Uses React context for global access throughout the app.
 */

import { createContext, useContext, useState, useCallback, ReactNode } from 'react';

// Toast types
export type ToastType = 'success' | 'error' | 'warning' | 'info';

export interface Toast {
    id: string;
    type: ToastType;
    title: string;
    message?: string;
    duration?: number;
}

interface ToastContextType {
    toasts: Toast[];
    addToast: (toast: Omit<Toast, 'id'>) => void;
    removeToast: (id: string) => void;
    success: (title: string, message?: string) => void;
    error: (title: string, message?: string) => void;
    warning: (title: string, message?: string) => void;
    info: (title: string, message?: string) => void;
}

const ToastContext = createContext<ToastContextType | null>(null);

export function useToast() {
    const context = useContext(ToastContext);
    if (!context) {
        throw new Error('useToast must be used within a ToastProvider');
    }
    return context;
}

interface ToastProviderProps {
    children: ReactNode;
}

export function ToastProvider({ children }: ToastProviderProps) {
    const [toasts, setToasts] = useState<Toast[]>([]);

    const removeToast = useCallback((id: string) => {
        setToasts((prev) => prev.filter((t) => t.id !== id));
    }, []);

    const addToast = useCallback((toast: Omit<Toast, 'id'>) => {
        const id = `toast-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;
        const duration = toast.duration ?? 5000;

        setToasts((prev) => [...prev, { ...toast, id }]);

        if (duration > 0) {
            setTimeout(() => removeToast(id), duration);
        }
    }, [removeToast]);

    const success = useCallback((title: string, message?: string) => {
        addToast({ type: 'success', title, message });
    }, [addToast]);

    const error = useCallback((title: string, message?: string) => {
        addToast({ type: 'error', title, message, duration: 8000 }); // Errors stay longer
    }, [addToast]);

    const warning = useCallback((title: string, message?: string) => {
        addToast({ type: 'warning', title, message });
    }, [addToast]);

    const info = useCallback((title: string, message?: string) => {
        addToast({ type: 'info', title, message });
    }, [addToast]);

    return (
        <ToastContext.Provider value={{ toasts, addToast, removeToast, success, error, warning, info }}>
            {children}
            <ToastContainer toasts={toasts} removeToast={removeToast} />
        </ToastContext.Provider>
    );
}

// Toast Container Component
function ToastContainer({ toasts, removeToast }: { toasts: Toast[]; removeToast: (id: string) => void }) {
    if (toasts.length === 0) return null;

    return (
        <div className="fixed bottom-4 right-4 z-50 flex flex-col gap-2 max-w-sm">
            {toasts.map((toast) => (
                <ToastItem key={toast.id} toast={toast} onClose={() => removeToast(toast.id)} />
            ))}
        </div>
    );
}

// Individual Toast Item
function ToastItem({ toast, onClose }: { toast: Toast; onClose: () => void }) {
    const icons = {
        success: '✅',
        error: '❌',
        warning: '⚠️',
        info: 'ℹ️',
    };

    const colors = {
        success: 'bg-green-900/90 border-green-500/50',
        error: 'bg-red-900/90 border-red-500/50',
        warning: 'bg-amber-900/90 border-amber-500/50',
        info: 'bg-blue-900/90 border-blue-500/50',
    };

    return (
        <div
            className={`${colors[toast.type]} backdrop-blur-sm rounded-lg p-4 shadow-xl border animate-slide-in-right`}
            role="alert"
        >
            <div className="flex items-start gap-3">
                <span className="text-xl">{icons[toast.type]}</span>
                <div className="flex-1 min-w-0">
                    <h4 className="text-white font-semibold text-sm">{toast.title}</h4>
                    {toast.message && (
                        <p className="text-slate-300 text-sm mt-1">{toast.message}</p>
                    )}
                </div>
                <button
                    onClick={onClose}
                    className="text-slate-400 hover:text-white transition-colors"
                    aria-label="Close notification"
                >
                    ✕
                </button>
            </div>
        </div>
    );
}

// Add to index.css for animation:
// @keyframes slide-in-right {
//     from { transform: translateX(100%); opacity: 0; }
//     to { transform: translateX(0); opacity: 1; }
// }
// .animate-slide-in-right { animation: slide-in-right 0.3s ease-out; }

export default ToastProvider;
