// Empty State Component
// ========================================
import { cn } from '@/lib/utils';

interface EmptyStateProps {
    icon?: string;
    title: string;
    description?: string;
    action?: {
        label: string;
        onClick: () => void;
    };
    className?: string;
}

export function EmptyState({ icon = '📭', title, description, action, className }: EmptyStateProps) {
    return (
        <div className={cn(
            'flex flex-col items-center justify-center p-12 text-center',
            'bg-white dark:bg-slate-800 rounded-xl border border-dashed border-slate-300 dark:border-slate-600',
            className
        )}>
            <div className="text-5xl mb-4">{icon}</div>
            <h3 className="text-lg font-semibold text-slate-900 dark:text-white mb-2">{title}</h3>
            {description && (
                <p className="text-slate-500 dark:text-slate-400 max-w-md mb-4">{description}</p>
            )}
            {action && (
                <button
                    onClick={action.onClick}
                    className="px-4 py-2 bg-indigo-600 text-white rounded-lg hover:bg-indigo-700 transition-colors"
                >
                    {action.label}
                </button>
            )}
        </div>
    );
}

export default EmptyState;
