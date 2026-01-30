/**
 * Pipeline Status Card
 * =====================
 * Compact status display for the analysis pipeline.
 * Shows cache status, last refresh, and refresh button.
 */

import { useSystemStatus, useRefreshAll } from '../hooks/useAnalysis';

interface PipelineStatusCardProps {
    compact?: boolean;
}

export function PipelineStatusCard({ compact = false }: PipelineStatusCardProps) {
    const { data: status, isLoading, isError } = useSystemStatus();
    const refreshAll = useRefreshAll();

    if (isLoading) {
        return (
            <div className="pipeline-card loading">
                <span className="spinner">⟳</span>
            </div>
        );
    }

    if (isError || !status) {
        return (
            <div className="pipeline-card error">
                <span>⚠️ Status unavailable</span>
            </div>
        );
    }

    return (
        <div className={`pipeline-card ${compact ? 'compact' : ''}`}>
            <div className="status-header">
                <span className={`status-dot ${status.status}`} />
                <span className="status-text">
                    Pipeline {status.status === 'healthy' ? 'Healthy' : 'Issues'}
                </span>
            </div>

            <div className="metrics">
                <div className="metric">
                    <span className="metric-value">{status.pipeline.agent_count}</span>
                    <span className="metric-label">Agents</span>
                </div>
                <div className="metric">
                    <span className="metric-value">{status.cache.hit_rate}</span>
                    <span className="metric-label">Cache Hit</span>
                </div>
                <div className="metric">
                    <span className="metric-value">{status.pipeline.total_executions}</span>
                    <span className="metric-label">Runs</span>
                </div>
            </div>

            <button
                className="refresh-btn"
                onClick={() => refreshAll.mutate()}
                disabled={refreshAll.isPending}
            >
                {refreshAll.isPending ? '⟳ Refreshing...' : '🔄 Refresh All'}
            </button>

            <style>{`
                .pipeline-card {
                    background: linear-gradient(135deg, rgba(59, 130, 246, 0.1), rgba(139, 92, 246, 0.1));
                    border: 1px solid rgba(59, 130, 246, 0.2);
                    border-radius: 12px;
                    padding: 16px;
                    color: white;
                }
                
                .pipeline-card.compact {
                    padding: 12px;
                }
                
                .pipeline-card.loading,
                .pipeline-card.error {
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    min-height: 100px;
                    color: rgba(255, 255, 255, 0.5);
                }
                
                .spinner {
                    animation: spin 1s linear infinite;
                    font-size: 24px;
                }
                
                @keyframes spin {
                    from { transform: rotate(0deg); }
                    to { transform: rotate(360deg); }
                }
                
                .status-header {
                    display: flex;
                    align-items: center;
                    gap: 8px;
                    margin-bottom: 16px;
                }
                
                .status-dot {
                    width: 10px;
                    height: 10px;
                    border-radius: 50%;
                    background: #10B981;
                }
                
                .status-dot.healthy {
                    background: #10B981;
                    box-shadow: 0 0 8px rgba(16, 185, 129, 0.5);
                }
                
                .status-dot.degraded {
                    background: #F59E0B;
                }
                
                .status-dot.unhealthy {
                    background: #EF4444;
                }
                
                .status-text {
                    font-size: 14px;
                    font-weight: 600;
                }
                
                .metrics {
                    display: flex;
                    gap: 24px;
                    margin-bottom: 16px;
                }
                
                .metric {
                    display: flex;
                    flex-direction: column;
                }
                
                .metric-value {
                    font-size: 18px;
                    font-weight: 700;
                    color: #3B82F6;
                }
                
                .metric-label {
                    font-size: 10px;
                    color: rgba(255, 255, 255, 0.5);
                    text-transform: uppercase;
                }
                
                .refresh-btn {
                    width: 100%;
                    padding: 10px;
                    background: linear-gradient(135deg, #3B82F6, #2563EB);
                    border: none;
                    border-radius: 8px;
                    color: white;
                    font-size: 13px;
                    font-weight: 500;
                    cursor: pointer;
                    transition: all 0.2s;
                }
                
                .refresh-btn:hover {
                    transform: translateY(-1px);
                    box-shadow: 0 4px 12px rgba(59, 130, 246, 0.4);
                }
                
                .refresh-btn:disabled {
                    opacity: 0.6;
                    cursor: not-allowed;
                    transform: none;
                }
            `}</style>
        </div>
    );
}

export default PipelineStatusCard;
