/**
 * Real-time Update Components
 * ===========================
 * UI components for showing cache status, loading states, and timestamps.
 */

import { useState, useEffect } from 'react';

// ========================================
// CACHE STATUS INDICATOR
// ========================================

interface CacheIndicatorProps {
    isCached: boolean;
    cacheAge: number | null;
    lastUpdated: Date | null;
    isRefreshing?: boolean;
    onRefresh?: () => void;
    compact?: boolean;
}

export function CacheIndicator({
    isCached,
    cacheAge,
    lastUpdated,
    isRefreshing = false,
    onRefresh,
    compact = false,
}: CacheIndicatorProps) {
    const [timeAgo, setTimeAgo] = useState('');

    // Update time ago every minute
    useEffect(() => {
        const updateTimeAgo = () => {
            if (lastUpdated) {
                const seconds = Math.floor((Date.now() - lastUpdated.getTime()) / 1000);
                if (seconds < 60) setTimeAgo('just now');
                else if (seconds < 3600) setTimeAgo(`${Math.floor(seconds / 60)}m ago`);
                else if (seconds < 86400) setTimeAgo(`${Math.floor(seconds / 3600)}h ago`);
                else setTimeAgo(`${Math.floor(seconds / 86400)}d ago`);
            }
        };

        updateTimeAgo();
        const interval = setInterval(updateTimeAgo, 60000);
        return () => clearInterval(interval);
    }, [lastUpdated]);

    if (compact) {
        return (
            <div className="cache-indicator-compact">
                <span className={`cache-dot ${isCached ? 'cached' : 'fresh'}`} />
                <span className="cache-time">{timeAgo}</span>
                {onRefresh && (
                    <button
                        onClick={onRefresh}
                        disabled={isRefreshing}
                        className="refresh-btn-compact"
                    >
                        {isRefreshing ? '...' : '↻'}
                    </button>
                )}
                <style>{compactStyles}</style>
            </div>
        );
    }

    return (
        <div className="cache-indicator">
            <div className="cache-status">
                <span className={`status-badge ${isCached ? 'cached' : 'fresh'}`}>
                    {isCached ? '📦 Cached' : '✨ Fresh'}
                </span>
                {cacheAge !== null && (
                    <span className="cache-age">
                        {cacheAge < 60
                            ? `${Math.floor(cacheAge)}s old`
                            : `${Math.floor(cacheAge / 60)}m old`
                        }
                    </span>
                )}
            </div>

            <div className="cache-timestamp">
                <span className="timestamp-label">Last updated:</span>
                <span className="timestamp-value">{timeAgo || 'unknown'}</span>
            </div>

            {onRefresh && (
                <button
                    onClick={onRefresh}
                    disabled={isRefreshing}
                    className="refresh-btn"
                >
                    {isRefreshing ? (
                        <span className="spinner">⟳</span>
                    ) : (
                        '🔄 Refresh'
                    )}
                </button>
            )}

            <style>{fullStyles}</style>
        </div>
    );
}

const compactStyles = `
    .cache-indicator-compact {
        display: inline-flex;
        align-items: center;
        gap: 6px;
        font-size: 12px;
        color: rgba(255, 255, 255, 0.6);
    }
    
    .cache-dot {
        width: 8px;
        height: 8px;
        border-radius: 50%;
    }
    
    .cache-dot.cached {
        background: #F59E0B;
    }
    
    .cache-dot.fresh {
        background: #10B981;
    }
    
    .refresh-btn-compact {
        background: transparent;
        border: none;
        color: rgba(255, 255, 255, 0.6);
        cursor: pointer;
        padding: 2px 4px;
        font-size: 14px;
    }
    
    .refresh-btn-compact:hover {
        color: white;
    }
`;

const fullStyles = `
    .cache-indicator {
        display: flex;
        align-items: center;
        gap: 16px;
        padding: 12px 16px;
        background: rgba(255, 255, 255, 0.05);
        border-radius: 8px;
        border: 1px solid rgba(255, 255, 255, 0.1);
    }
    
    .cache-status {
        display: flex;
        align-items: center;
        gap: 8px;
    }
    
    .status-badge {
        padding: 4px 10px;
        border-radius: 12px;
        font-size: 12px;
        font-weight: 500;
    }
    
    .status-badge.cached {
        background: rgba(245, 158, 11, 0.2);
        color: #F59E0B;
    }
    
    .status-badge.fresh {
        background: rgba(16, 185, 129, 0.2);
        color: #10B981;
    }
    
    .cache-age {
        font-size: 12px;
        color: rgba(255, 255, 255, 0.5);
    }
    
    .cache-timestamp {
        display: flex;
        align-items: center;
        gap: 6px;
        font-size: 12px;
    }
    
    .timestamp-label {
        color: rgba(255, 255, 255, 0.5);
    }
    
    .timestamp-value {
        color: rgba(255, 255, 255, 0.8);
    }
    
    .refresh-btn {
        background: linear-gradient(135deg, #3B82F6, #2563EB);
        border: none;
        padding: 8px 14px;
        border-radius: 6px;
        color: white;
        font-size: 12px;
        cursor: pointer;
        display: flex;
        align-items: center;
        gap: 4px;
        transition: all 0.2s;
    }
    
    .refresh-btn:hover {
        transform: translateY(-1px);
        box-shadow: 0 4px 12px rgba(59, 130, 246, 0.4);
    }
    
    .refresh-btn:disabled {
        opacity: 0.6;
        cursor: not-allowed;
    }
    
    .spinner {
        animation: spin 1s linear infinite;
    }
    
    @keyframes spin {
        from { transform: rotate(0deg); }
        to { transform: rotate(360deg); }
    }
`;


// ========================================
// LOADING SKELETON
// ========================================

interface LoadingSkeletonProps {
    variant?: 'card' | 'table' | 'chart' | 'text';
    count?: number;
}

export function LoadingSkeleton({ variant = 'card', count = 1 }: LoadingSkeletonProps) {
    const items = Array.from({ length: count }, (_, i) => i);

    if (variant === 'card') {
        return (
            <div className="skeleton-container">
                {items.map(i => (
                    <div key={i} className="skeleton-card">
                        <div className="skeleton-shimmer skeleton-title" />
                        <div className="skeleton-shimmer skeleton-text" />
                        <div className="skeleton-shimmer skeleton-text short" />
                    </div>
                ))}
                <style>{skeletonStyles}</style>
            </div>
        );
    }

    if (variant === 'table') {
        return (
            <div className="skeleton-table">
                {items.map(i => (
                    <div key={i} className="skeleton-row">
                        <div className="skeleton-shimmer skeleton-cell" />
                        <div className="skeleton-shimmer skeleton-cell" />
                        <div className="skeleton-shimmer skeleton-cell" />
                        <div className="skeleton-shimmer skeleton-cell short" />
                    </div>
                ))}
                <style>{skeletonStyles}</style>
            </div>
        );
    }

    if (variant === 'chart') {
        return (
            <div className="skeleton-chart">
                <div className="skeleton-shimmer skeleton-chart-box" />
                <style>{skeletonStyles}</style>
            </div>
        );
    }

    return (
        <div className="skeleton-text-block">
            {items.map(i => (
                <div key={i} className="skeleton-shimmer skeleton-text" />
            ))}
            <style>{skeletonStyles}</style>
        </div>
    );
}

const skeletonStyles = `
    .skeleton-shimmer {
        background: linear-gradient(
            90deg,
            rgba(255, 255, 255, 0.05) 25%,
            rgba(255, 255, 255, 0.1) 50%,
            rgba(255, 255, 255, 0.05) 75%
        );
        background-size: 200% 100%;
        animation: shimmer 1.5s infinite;
        border-radius: 4px;
    }
    
    @keyframes shimmer {
        0% { background-position: 200% 0; }
        100% { background-position: -200% 0; }
    }
    
    .skeleton-container {
        display: grid;
        gap: 16px;
    }
    
    .skeleton-card {
        padding: 20px;
        background: rgba(255, 255, 255, 0.02);
        border-radius: 8px;
        border: 1px solid rgba(255, 255, 255, 0.05);
    }
    
    .skeleton-title {
        height: 24px;
        width: 60%;
        margin-bottom: 12px;
    }
    
    .skeleton-text {
        height: 14px;
        width: 100%;
        margin-bottom: 8px;
    }
    
    .skeleton-text.short {
        width: 40%;
    }
    
    .skeleton-table {
        display: flex;
        flex-direction: column;
        gap: 8px;
    }
    
    .skeleton-row {
        display: grid;
        grid-template-columns: 2fr 1fr 1fr 0.5fr;
        gap: 12px;
    }
    
    .skeleton-cell {
        height: 36px;
    }
    
    .skeleton-chart-box {
        height: 200px;
        width: 100%;
    }
`;


// ========================================
// LIVE UPDATE BADGE
// ========================================

interface LiveBadgeProps {
    isLive: boolean;
    pollingInterval?: number;
}

export function LiveBadge({ isLive, pollingInterval = 30000 }: LiveBadgeProps) {
    return (
        <div className="live-badge">
            <span className={`live-dot ${isLive ? 'active' : 'paused'}`} />
            <span className="live-text">
                {isLive ? 'Live' : 'Paused'}
            </span>
            {isLive && (
                <span className="live-interval">
                    ({Math.round(pollingInterval / 1000)}s)
                </span>
            )}
            <style>{`
                .live-badge {
                    display: inline-flex;
                    align-items: center;
                    gap: 6px;
                    padding: 4px 10px;
                    background: rgba(255, 255, 255, 0.05);
                    border-radius: 12px;
                    font-size: 11px;
                    text-transform: uppercase;
                    letter-spacing: 0.5px;
                }
                
                .live-dot {
                    width: 6px;
                    height: 6px;
                    border-radius: 50%;
                    animation: pulse 2s infinite;
                }
                
                .live-dot.active {
                    background: #10B981;
                }
                
                .live-dot.paused {
                    background: #6B7280;
                    animation: none;
                }
                
                @keyframes pulse {
                    0%, 100% { opacity: 1; }
                    50% { opacity: 0.4; }
                }
                
                .live-text {
                    color: rgba(255, 255, 255, 0.8);
                }
                
                .live-interval {
                    color: rgba(255, 255, 255, 0.4);
                }
            `}</style>
        </div>
    );
}


// ========================================
// EXPORTS
// ========================================

export default CacheIndicator;
