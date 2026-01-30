// Toast Notification Component
// ========================================
import { useState, useEffect, createContext, useContext, type ReactNode } from 'react';
import { cn } from '@/lib/utils';

interface Toast {
    id: string;
    type: 'success' | 'error' | 'warning' | 'info';
    title: string;
    message?: string;
    duration?: number;
}

interface ToastContextType {
    toasts: Toast[];
    addToast: (toast: Omit<Toast, 'id'>) => void;
    removeToast: (id: string) => void;
}

const ToastContext = createContext<ToastContextType | null>(null);

export function ToastProvider({ children }: { children: ReactNode }) {
    const [toasts, setToasts] = useState<Toast[]>([]);

    const addToast = (toast: Omit<Toast, 'id'>) => {
        const id = Math.random().toString(36).substring(7);
        setToasts(prev => [...prev, { ...toast, id }]);
    };

    const removeToast = (id: string) => {
        setToasts(prev => prev.filter(t => t.id !== id));
    };

    return (
        <ToastContext.Provider value={{ toasts, addToast, removeToast }}>
            {children}
            <ToastContainer toasts={toasts} removeToast={removeToast} />
        </ToastContext.Provider>
    );
}

export function useToast() {
    const context = useContext(ToastContext);
    if (!context) {
        throw new Error('useToast must be used within a ToastProvider');
    }
    return context;
}

function ToastContainer({ toasts, removeToast }: { toasts: Toast[]; removeToast: (id: string) => void }) {
    return (
        <div className="fixed bottom-4 right-4 z-50 flex flex-col gap-2">
            {toasts.map(toast => (
                <ToastItem key={toast.id} toast={toast} onClose={() => removeToast(toast.id)} />
            ))}
        </div>
    );
}

function ToastItem({ toast, onClose }: { toast: Toast; onClose: () => void }) {
    useEffect(() => {
        const timer = setTimeout(onClose, toast.duration || 5000);
        return () => clearTimeout(timer);
    }, [toast.duration, onClose]);

    const icons = {
        success: '✓',
        error: '✕',
        warning: '⚠',
        info: 'ℹ',
    };

    const colors = {
        success: 'bg-green-500',
        error: 'bg-red-500',
        warning: 'bg-amber-500',
        info: 'bg-blue-500',
    };

    return (
        <div className={cn(
            'flex items-start gap-3 p-4 rounded-lg shadow-lg min-w-[300px] max-w-md',
            'bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700',
            'animate-in slide-in-from-right-full duration-300'
        )}>
            <div className={cn('w-6 h-6 rounded-full flex items-center justify-center text-white text-sm', colors[toast.type])}>
                {icons[toast.type]}
            </div>
            <div className="flex-1">
                <h4 className="font-medium text-slate-900 dark:text-white">{toast.title}</h4>
                {toast.message && (
                    <p className="text-sm text-slate-500 dark:text-slate-400 mt-1">{toast.message}</p>
                )}
            </div>
            <button
                onClick={onClose}
                className="text-slate-400 hover:text-slate-600 dark:hover:text-slate-300"
            >
                ✕
            </button>
        </div>
    );
}

export default ToastProvider;
