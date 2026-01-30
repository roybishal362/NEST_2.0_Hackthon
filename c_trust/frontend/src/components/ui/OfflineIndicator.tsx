// Offline Indicator Component
// ========================================
import { useState, useEffect } from 'react';
import { cn } from '@/lib/utils';

export function OfflineIndicator() {
    const [isOnline, setIsOnline] = useState(navigator.onLine);
    const [showBanner, setShowBanner] = useState(false);

    useEffect(() => {
        const handleOnline = () => {
            setIsOnline(true);
            // Show "back online" message briefly
            setShowBanner(true);
            setTimeout(() => setShowBanner(false), 3000);
        };

        const handleOffline = () => {
            setIsOnline(false);
            setShowBanner(true);
        };

        window.addEventListener('online', handleOnline);
        window.addEventListener('offline', handleOffline);

        return () => {
            window.removeEventListener('online', handleOnline);
            window.removeEventListener('offline', handleOffline);
        };
    }, []);

    if (!showBanner && isOnline) return null;

    return (
        <div className={cn(
            'fixed top-0 left-0 right-0 z-50 py-2 px-4 text-center text-sm font-medium transition-all duration-300',
            isOnline 
                ? 'bg-green-500 text-white' 
                : 'bg-amber-500 text-white'
        )}>
            {isOnline ? (
                <span>✓ Back online - Data synced</span>
            ) : (
                <span>⚠ You're offline - Showing cached data</span>
            )}
        </div>
    );
}

export default OfflineIndicator;
