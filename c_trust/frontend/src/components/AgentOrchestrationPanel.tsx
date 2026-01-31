/**
 * Agent Orchestration Panel
 * ==========================
 * Visual pipeline showing all 7 AI agents running in parallel,
 * feeding into Consensus Engine and DQI calculation.
 * 
 * Features:
 * - Live status per agent (running/complete/error)
 * - Confidence meters
 * - Signal flow visualization
 * - Processing time display
 */

import { useAnalysis, type AgentSignal } from '../hooks/useAnalysis';
import { CacheIndicator, LiveBadge } from './RealTimeIndicators';

// Agent configuration with icons and colors
const AGENT_CONFIG: Record<string, { icon: string; color: string; description: string }> = {
    'Data Completeness': {
        icon: '📊',
        color: '#3B82F6',
        description: 'Monitors data completeness rates',
    },
    'Safety & Compliance': {
        icon: '🛡️',
        color: '#EF4444',
        description: 'Detects safety signals and SAE issues',
    },
    'Query Quality': {
        icon: '❓',
        color: '#8B5CF6',
        description: 'Analyzes query patterns and resolution',
    },
    'Coding Readiness': {
        icon: '🏷️',
        color: '#F59E0B',
        description: 'MedDRA/WHODD coding completion',
    },
    'Stability': {
        icon: '📈',
        color: '#10B981',
        description: 'Enrollment velocity and site activation',
    },
    'Temporal Drift': {
        icon: '⏰',
        color: '#EC4899',
        description: 'Data entry lag trends',
    },
    'Cross-Evidence': {
        icon: '🔗',
        color: '#06B6D4',
        description: 'Cross-source validation',
    },
};

// Risk level colors
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

interface AgentCardProps {
    signal: AgentSignal;
    isRunning?: boolean;
}

function AgentCard({ signal, isRunning = false }: AgentCardProps) {
    const config = AGENT_CONFIG[signal.agent_name] || {
        icon: '🤖',
        color: '#6B7280',
        description: 'AI Agent',
    };

    const hasError = !!signal.error;
    const abstained = signal.abstained;
    const confidence = signal.confidence ?? 0;

    return (
        <div
            className={`agent-card ${hasError ? 'error' : ''} ${abstained ? 'abstained' : ''} ${isRunning ? 'running' : ''}`}
            style={{ borderColor: config.color }}
        >
            <div className="agent-header">
                <span className="agent-icon">{config.icon}</span>
                <span className="agent-name">{signal.agent_name}</span>
            </div>

            <div className="agent-body">
                {/* Status */}
                <div className="status-row">
                    {hasError ? (
                        <span className="status error">❌ Error</span>
                    ) : abstained ? (
                        <span className="status abstained">⏸️ Abstained</span>
                    ) : isRunning ? (
                        <span className="status running">⏳ Running...</span>
                    ) : (
                        <span className="status success">✅ Complete</span>
                    )}
                </div>

                {/* Risk Level */}
                {signal.risk_level && (
                    <div className="risk-row">
                        <span
                            className="risk-badge"
                            style={{ background: getRiskColor(signal.risk_level) }}
                        >
                            {signal.risk_level}
                        </span>
                    </div>
                )}

                {/* Confidence Meter */}
                {!hasError && !abstained && (
                    <div className="confidence-row">
                        <div className="confidence-bar">
                            <div
                                className="confidence-fill"
                                style={{
                                    width: `${confidence * 100}%`,
                                    background: config.color,
                                }}
                            />
                        </div>
                        <span className="confidence-value">
                            {(confidence * 100).toFixed(0)}%
                        </span>
                    </div>
                )}

                {/* Processing Time */}
                <div className="time-row">
                    <span className="time-value">
                        {signal.processing_time_ms.toFixed(0)}ms
                    </span>
                </div>
            </div>
        </div>
    );
}

interface AgentOrchestrationPanelProps {
    studyId: string;
    compact?: boolean;
}

export function AgentOrchestrationPanel({ studyId, compact = false }: AgentOrchestrationPanelProps) {
    const {
        data,
        isLoading,
        isFetching,
        isRefreshing,
        isError,
        cacheInfo,
        refresh,
    } = useAnalysis(studyId, { pollingInterval: 30000 });

    if (isLoading) {
        return (
            <div className="orchestration-panel loading">
                <div className="loading-spinner">⟳</div>
                <p>Loading agent analysis...</p>
            </div>
        );
    }

    if (isError || !data) {
        return (
            <div className="orchestration-panel error">
                <p>❌ Failed to load agent data</p>
            </div>
        );
    }

    return (
        <div className={`orchestration-panel ${compact ? 'compact' : ''}`}>
            {/* Header */}
            <header className="panel-header">
                <div className="header-left">
                    <h2>🤖 Agent Orchestration</h2>
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

            {/* Agent Grid - 7 Agents */}
            <section className="agents-grid">
                {data.agent_signals.map((signal) => (
                    <AgentCard
                        key={signal.agent_name}
                        signal={signal}
                        isRunning={isFetching}
                    />
                ))}
            </section>

            {/* Animated Data Flow Visualization */}
            <div className="flow-section">
                <svg className="flow-svg" viewBox="0 0 400 60" xmlns="http://www.w3.org/2000/svg">
                    {/* Background glow */}
                    <defs>
                        <linearGradient id="flowGradient" x1="0%" y1="0%" x2="0%" y2="100%">
                            <stop offset="0%" stopColor="#3B82F6" stopOpacity="0.2" />
                            <stop offset="50%" stopColor="#8B5CF6" stopOpacity="0.6" />
                            <stop offset="100%" stopColor="#8B5CF6" stopOpacity="0.2" />
                        </linearGradient>
                        <filter id="glow">
                            <feGaussianBlur stdDeviation="2" result="coloredBlur" />
                            <feMerge>
                                <feMergeNode in="coloredBlur" />
                                <feMergeNode in="SourceGraphic" />
                            </feMerge>
                        </filter>
                    </defs>

                    {/* Flow lines from agents */}
                    {[0, 1, 2, 3, 4, 5, 6].map((i) => (
                        <g key={i}>
                            <line
                                x1={30 + i * 50}
                                y1="5"
                                x2="200"
                                y2="55"
                                stroke="url(#flowGradient)"
                                strokeWidth="2"
                                opacity="0.5"
                            />
                            {/* Animated dot */}
                            <circle
                                r="3"
                                fill="#8B5CF6"
                                filter="url(#glow)"
                            >
                                <animateMotion
                                    dur={`${1.5 + i * 0.2}s`}
                                    repeatCount="indefinite"
                                    path={`M${30 + i * 50},5 L200,55`}
                                />
                            </circle>
                        </g>
                    ))}

                    {/* Central flow arrow */}
                    <path
                        d="M200,25 L200,55"
                        stroke="#8B5CF6"
                        strokeWidth="3"
                        fill="none"
                        markerEnd="url(#arrowhead)"
                    />
                    <defs>
                        <marker id="arrowhead" markerWidth="10" markerHeight="7" refX="0" refY="3.5" orient="auto">
                            <polygon points="0 0, 10 3.5, 0 7" fill="#8B5CF6" />
                        </marker>
                    </defs>
                </svg>
                <div className="flow-label-container">
                    <span className="flow-label">
                        <span className="flow-pulse"></span>
                        Signals aggregating to Consensus Engine
                    </span>
                </div>
            </div>

            {/* Consensus Engine */}
            <section className="consensus-section">
                <div className="engine-card consensus">
                    <div className="engine-header">
                        <span className="engine-icon">⚖️</span>
                        <span className="engine-name">Consensus Engine</span>
                    </div>
                    <div className="engine-body">
                        <div className="metric">
                            <span className="metric-label">Risk Level</span>
                            <span
                                className="metric-value risk"
                                style={{ color: getRiskColor(data.consensus?.risk_level || null) }}
                            >
                                {data.consensus?.risk_level || 'N/A'}
                            </span>
                        </div>
                        <div className="metric">
                            <span className="metric-label">Confidence</span>
                            <span className="metric-value">
                                {data.consensus?.confidence
                                    ? `${(data.consensus.confidence * 100).toFixed(0)}%`
                                    : 'N/A'
                                }
                            </span>
                        </div>
                        <div className="metric">
                            <span className="metric-label">Action</span>
                            <span className="metric-value action">
                                {data.consensus?.recommended_action || 'N/A'}
                            </span>
                        </div>
                    </div>
                </div>
            </section>

            {/* Flow Arrow */}
            <div className="flow-section small">
                <span className="flow-arrow">↓</span>
            </div>

            {/* DQI Score */}
            <section className="dqi-section">
                <div className="engine-card dqi">
                    <div className="engine-header">
                        <span className="engine-icon">📊</span>
                        <span className="engine-name">Data Quality Index</span>
                    </div>
                    <div className="engine-body">
                        <div className="dqi-score">
                            <span
                                className="score-value"
                                style={{ color: getRiskColor(data.dqi_score?.risk_level || null) }}
                            >
                                {data.dqi_score?.overall_score.toFixed(1) || 'N/A'}
                            </span>
                            <span className="score-label">/ 100</span>
                        </div>
                        <div className="dqi-threshold">
                            {data.dqi_score?.threshold_met || 'Unknown'}
                        </div>
                    </div>
                </div>
            </section>

            {/* Summary Stats */}
            <section className="summary-section">
                <div className="stat">
                    <span className="stat-value">{data.agents_succeeded}</span>
                    <span className="stat-label">Succeeded</span>
                </div>
                <div className="stat">
                    <span className="stat-value">{data.agents_failed}</span>
                    <span className="stat-label">Failed</span>
                </div>
                <div className="stat">
                    <span className="stat-value">{data.agents_abstained}</span>
                    <span className="stat-label">Abstained</span>
                </div>
                <div className="stat">
                    <span className="stat-value">{data.processing_time_ms.toFixed(0)}ms</span>
                    <span className="stat-label">Total Time</span>
                </div>
            </section>

            <style>{styles}</style>
        </div>
    );
}

const styles = `
    .orchestration-panel {
        background: linear-gradient(135deg, #1e293b, #0f172a);
        border-radius: 16px;
        padding: 24px;
        border: 1px solid rgba(255, 255, 255, 0.1);
        color: white;
    }
    
    .orchestration-panel.compact {
        padding: 16px;
    }
    
    .orchestration-panel.loading,
    .orchestration-panel.error {
        min-height: 300px;
        display: flex;
        flex-direction: column;
        align-items: center;
        justify-content: center;
        color: rgba(255, 255, 255, 0.6);
    }
    
    .loading-spinner {
        font-size: 32px;
        animation: spin 1s linear infinite;
        margin-bottom: 12px;
    }
    
    @keyframes spin {
        from { transform: rotate(0deg); }
        to { transform: rotate(360deg); }
    }
    
    /* Header */
    .panel-header {
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
        font-weight: 600;
    }
    
    /* Agent Grid */
    .agents-grid {
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(160px, 1fr));
        gap: 16px;
        margin-bottom: 20px;
    }
    
    .agent-card {
        background: rgba(255, 255, 255, 0.05);
        border-radius: 12px;
        padding: 16px;
        border-left: 3px solid;
        transition: all 0.2s;
    }
    
    .agent-card:hover {
        background: rgba(255, 255, 255, 0.08);
        transform: translateY(-2px);
    }
    
    .agent-card.error {
        border-left-color: #EF4444 !important;
        opacity: 0.7;
    }
    
    .agent-card.abstained {
        border-left-color: #6B7280 !important;
        opacity: 0.7;
    }
    
    .agent-card.running {
        animation: pulse-border 1.5s infinite;
    }
    
    @keyframes pulse-border {
        0%, 100% { box-shadow: 0 0 0 0 rgba(59, 130, 246, 0.2); }
        50% { box-shadow: 0 0 0 4px rgba(59, 130, 246, 0.2); }
    }
    
    .agent-header {
        display: flex;
        align-items: center;
        gap: 8px;
        margin-bottom: 12px;
    }
    
    .agent-icon {
        font-size: 20px;
    }
    
    .agent-name {
        font-size: 13px;
        font-weight: 500;
        color: rgba(255, 255, 255, 0.9);
    }
    
    .agent-body {
        display: flex;
        flex-direction: column;
        gap: 8px;
    }
    
    .status-row .status {
        font-size: 11px;
        padding: 2px 6px;
        border-radius: 4px;
        background: rgba(255, 255, 255, 0.1);
    }
    
    .risk-badge {
        font-size: 10px;
        font-weight: 600;
        padding: 2px 8px;
        border-radius: 4px;
        text-transform: uppercase;
    }
    
    .confidence-row {
        display: flex;
        align-items: center;
        gap: 8px;
    }
    
    .confidence-bar {
        flex: 1;
        height: 4px;
        background: rgba(255, 255, 255, 0.1);
        border-radius: 2px;
        overflow: hidden;
    }
    
    .confidence-fill {
        height: 100%;
        border-radius: 2px;
        transition: width 0.3s;
    }
    
    .confidence-value {
        font-size: 11px;
        color: rgba(255, 255, 255, 0.6);
        min-width: 32px;
    }
    
    .time-row {
        font-size: 10px;
        color: rgba(255, 255, 255, 0.4);
    }
    
    /* Flow Arrows */
    .flow-section {
        display: flex;
        justify-content: center;
        padding: 12px 0;
    }
    
    .flow-section.small {
        padding: 8px 0;
    }
    
    .flow-arrow {
        display: flex;
        align-items: center;
        gap: 8px;
        color: rgba(255, 255, 255, 0.4);
        font-size: 18px;
    }
    
    .flow-label {
        font-size: 12px;
    }
    
    /* Engine Cards */
    .consensus-section,
    .dqi-section {
        display: flex;
        justify-content: center;
    }
    
    .engine-card {
        background: rgba(255, 255, 255, 0.05);
        border-radius: 12px;
        padding: 20px;
        min-width: 320px;
        border: 1px solid rgba(255, 255, 255, 0.1);
    }
    
    .engine-card.consensus {
        border-color: rgba(139, 92, 246, 0.3);
    }
    
    .engine-card.dqi {
        border-color: rgba(59, 130, 246, 0.3);
    }
    
    .engine-header {
        display: flex;
        align-items: center;
        gap: 10px;
        margin-bottom: 16px;
    }
    
    .engine-icon {
        font-size: 24px;
    }
    
    .engine-name {
        font-size: 16px;
        font-weight: 600;
    }
    
    .engine-body {
        display: flex;
        flex-wrap: wrap;
        gap: 16px;
    }
    
    .metric {
        display: flex;
        flex-direction: column;
        gap: 4px;
    }
    
    .metric-label {
        font-size: 11px;
        color: rgba(255, 255, 255, 0.5);
        text-transform: uppercase;
    }
    
    .metric-value {
        font-size: 16px;
        font-weight: 600;
    }
    
    .metric-value.risk {
        text-transform: uppercase;
    }
    
    .metric-value.action {
        font-size: 12px;
        font-weight: 500;
    }
    
    /* DQI Score */
    .dqi-score {
        display: flex;
        align-items: baseline;
        gap: 4px;
    }
    
    .score-value {
        font-size: 36px;
        font-weight: 700;
    }
    
    .score-label {
        font-size: 14px;
        color: rgba(255, 255, 255, 0.5);
    }
    
    .dqi-threshold {
        font-size: 12px;
        color: rgba(255, 255, 255, 0.6);
        margin-top: 4px;
    }
    
    /* Summary Stats */
    .summary-section {
        display: flex;
        justify-content: center;
        gap: 32px;
        margin-top: 24px;
        padding-top: 20px;
        border-top: 1px solid rgba(255, 255, 255, 0.1);
    }
    
    .stat {
        display: flex;
        flex-direction: column;
        align-items: center;
    }
    
    .stat-value {
        font-size: 20px;
        font-weight: 600;
    }
    
    .stat-label {
        font-size: 11px;
        color: rgba(255, 255, 255, 0.5);
        text-transform: uppercase;
    }
`;

export default AgentOrchestrationPanel;
