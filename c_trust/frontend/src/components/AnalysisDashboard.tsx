/**
 * Analysis Dashboard Widget
 * ==========================
 * Real-time study analysis display with all 7 agent signals.
 */

import { useAnalysis } from '../hooks/useAnalysis';
import { CacheIndicator, LoadingSkeleton, LiveBadge } from './RealTimeIndicators';

interface AnalysisDashboardProps {
    studyId: string;
    compact?: boolean;
}

export function AnalysisDashboard({ studyId, compact = false }: AnalysisDashboardProps) {
    const {
        data,
        isLoading,
        isFetching,
        isRefreshing,
        isError,
        error,
        cacheInfo,
        refresh,
    } = useAnalysis(studyId, {
        pollingInterval: 30000,
    });

    if (isLoading) {
        return (
            <div className="analysis-dashboard loading">
                <LoadingSkeleton variant="card" count={3} />
            </div>
        );
    }

    if (isError) {
        return (
            <div className="analysis-dashboard error">
                <div className="error-message">
                    ❌ Failed to load analysis: {error?.message || 'Unknown error'}
                </div>
            </div>
        );
    }

    if (!data) {
        return null;
    }

    const getRiskColor = (risk: string | null) => {
        if (!risk) return '#6B7280';
        switch (risk.toLowerCase()) {
            case 'critical': return '#EF4444';
            case 'high': return '#F59E0B';
            case 'medium': return '#3B82F6';
            case 'low': return '#10B981';
            default: return '#6B7280';
        }
    };

    return (
        <div className={`analysis-dashboard ${compact ? 'compact' : ''}`}>
            {/* Header with cache info */}
            <header className="dashboard-header">
                <div className="header-left">
                    <h2>Analysis: {studyId}</h2>
                    <LiveBadge isLive={true} pollingInterval={30000} />
                </div>
                <CacheIndicator
                    isCached={cacheInfo.isCached}
                    cacheAge={cacheInfo.cacheAge}
                    lastUpdated={cacheInfo.lastUpdated}
                    isRefreshing={isRefreshing || isFetching}
                    onRefresh={refresh}
                    compact={compact}
                />
            </header>

            {/* Summary Cards */}
            <section className="summary-cards">
                {/* DQI Score */}
                <div className="summary-card dqi">
                    <div className="card-icon">📊</div>
                    <div className="card-content">
                        <span className="card-value" style={{ color: getRiskColor(data.dqi_score?.risk_level || null) }}>
                            {data.dqi_score?.overall_score.toFixed(1) || 'N/A'}
                        </span>
                        <span className="card-label">DQI Score</span>
                    </div>
                </div>

                {/* Consensus Risk */}
                <div className="summary-card risk">
                    <div className="card-icon">⚠️</div>
                    <div className="card-content">
                        <span className="card-value" style={{ color: getRiskColor(data.consensus?.risk_level || null) }}>
                            {data.consensus?.risk_level || 'Unknown'}
                        </span>
                        <span className="card-label">Risk Level</span>
                    </div>
                </div>

                {/* Agents */}
                <div className="summary-card agents">
                    <div className="card-icon">🤖</div>
                    <div className="card-content">
                        <span className="card-value">
                            {data.agents_succeeded}/{data.agent_signals.length}
                        </span>
                        <span className="card-label">Agents OK</span>
                    </div>
                </div>

                {/* Processing Time */}
                <div className="summary-card time">
                    <div className="card-icon">⏱️</div>
                    <div className="card-content">
                        <span className="card-value">
                            {data.processing_time_ms.toFixed(0)}ms
                        </span>
                        <span className="card-label">Processing</span>
                    </div>
                </div>
            </section>

            {/* Agent Signals Table */}
            <section className="agent-signals">
                <h3>Agent Signals</h3>
                <table>
                    <thead>
                        <tr>
                            <th>Agent</th>
                            <th>Risk</th>
                            <th>Confidence</th>
                            <th>Status</th>
                        </tr>
                    </thead>
                    <tbody>
                        {data.agent_signals.map((signal) => (
                            <tr key={signal.agent_name}>
                                <td>{signal.agent_name}</td>
                                <td>
                                    <span
                                        className="risk-badge"
                                        style={{ background: getRiskColor(signal.risk_level) }}
                                    >
                                        {signal.risk_level || 'N/A'}
                                    </span>
                                </td>
                                <td>
                                    {signal.confidence
                                        ? `${(signal.confidence * 100).toFixed(0)}%`
                                        : '—'
                                    }
                                </td>
                                <td>
                                    {signal.error ? (
                                        <span className="status error">❌ Error</span>
                                    ) : signal.abstained ? (
                                        <span className="status abstained">⏸️ Abstained</span>
                                    ) : (
                                        <span className="status success">✅ OK</span>
                                    )}
                                </td>
                            </tr>
                        ))}
                    </tbody>
                </table>
            </section>

            {/* Consensus Explanation */}
            {data.consensus?.explanation && (
                <section className="consensus-explanation">
                    <h3>Consensus Explanation</h3>
                    <p>{data.consensus.explanation}</p>
                    <p className="recommended-action">
                        <strong>Recommended:</strong> {data.consensus.recommended_action}
                    </p>
                </section>
            )}

            <style>{`
                .analysis-dashboard {
                    padding: 24px;
                    background: linear-gradient(135deg, #1e293b, #0f172a);
                    border-radius: 12px;
                    border: 1px solid rgba(255, 255, 255, 0.1);
                    color: white;
                }
                
                .analysis-dashboard.compact {
                    padding: 16px;
                }
                
                .analysis-dashboard.loading {
                    min-height: 300px;
                }
                
                .dashboard-header {
                    display: flex;
                    justify-content: space-between;
                    align-items: center;
                    margin-bottom: 24px;
                }
                
                .header-left {
                    display: flex;
                    align-items: center;
                    gap: 12px;
                }
                
                .header-left h2 {
                    margin: 0;
                    font-size: 20px;
                }
                
                .summary-cards {
                    display: grid;
                    grid-template-columns: repeat(4, 1fr);
                    gap: 16px;
                    margin-bottom: 24px;
                }
                
                .summary-card {
                    display: flex;
                    align-items: center;
                    gap: 12px;
                    padding: 16px;
                    background: rgba(255, 255, 255, 0.05);
                    border-radius: 8px;
                }
                
                .card-icon {
                    font-size: 28px;
                }
                
                .card-content {
                    display: flex;
                    flex-direction: column;
                }
                
                .card-value {
                    font-size: 24px;
                    font-weight: 700;
                }
                
                .card-label {
                    font-size: 12px;
                    color: rgba(255, 255, 255, 0.6);
                }
                
                .agent-signals {
                    margin-bottom: 24px;
                }
                
                .agent-signals h3 {
                    margin: 0 0 16px 0;
                    font-size: 16px;
                }
                
                .agent-signals table {
                    width: 100%;
                    border-collapse: collapse;
                }
                
                .agent-signals th,
                .agent-signals td {
                    padding: 12px;
                    text-align: left;
                    border-bottom: 1px solid rgba(255, 255, 255, 0.1);
                }
                
                .agent-signals th {
                    color: rgba(255, 255, 255, 0.6);
                    font-weight: 500;
                    font-size: 12px;
                    text-transform: uppercase;
                }
                
                .risk-badge {
                    padding: 4px 8px;
                    border-radius: 4px;
                    font-size: 11px;
                    font-weight: 600;
                    text-transform: uppercase;
                }
                
                .status {
                    font-size: 12px;
                }
                
                .consensus-explanation {
                    padding: 16px;
                    background: rgba(59, 130, 246, 0.1);
                    border: 1px solid rgba(59, 130, 246, 0.3);
                    border-radius: 8px;
                }
                
                .consensus-explanation h3 {
                    margin: 0 0 8px 0;
                    font-size: 14px;
                }
                
                .consensus-explanation p {
                    margin: 0 0 8px 0;
                    font-size: 14px;
                    line-height: 1.5;
                    color: rgba(255, 255, 255, 0.8);
                }
                
                .recommended-action {
                    color: #3B82F6;
                }
                
                .error-message {
                    padding: 20px;
                    text-align: center;
                    color: #EF4444;
                }
                
                @media (max-width: 768px) {
                    .summary-cards {
                        grid-template-columns: repeat(2, 1fr);
                    }
                }
            `}</style>
        </div>
    );
}

export default AnalysisDashboard;
