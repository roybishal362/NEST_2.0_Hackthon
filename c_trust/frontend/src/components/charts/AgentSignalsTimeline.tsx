/**
 * Agent Signals Timeline
 * =======================
 * Historical view of agent signals over time.
 * Stacked area or line chart showing signal levels.
 */

import { useMemo } from 'react';

interface TimelineDataPoint {
    timestamp: string;
    agents: Record<string, {
        risk_level: string;
        confidence: number;
    }>;
}

interface AgentSignalsTimelineProps {
    data?: TimelineDataPoint[];
    height?: number;
}

// Mock historical data generator
function generateMockTimelineData(): TimelineDataPoint[] {
    const agents = [
        'Data Completeness',
        'Safety & Compliance',
        'Query Quality',
        'Coding Readiness',
        'Stability',
        'Temporal Drift',
        'Cross-Evidence'
    ];

    const riskLevels = ['Low', 'Medium', 'High', 'Critical'];
    const points: TimelineDataPoint[] = [];

    for (let i = 0; i < 12; i++) {
        const timestamp = new Date(Date.now() - (11 - i) * 3600000 * 2).toISOString();
        const agentsData: Record<string, { risk_level: string; confidence: number }> = {};

        agents.forEach(agent => {
            agentsData[agent] = {
                risk_level: riskLevels[Math.floor(Math.random() * 3)],
                confidence: 0.7 + Math.random() * 0.25,
            };
        });

        points.push({ timestamp, agents: agentsData });
    }

    return points;
}

const AGENT_COLORS: Record<string, string> = {
    'Data Completeness': '#3B82F6',
    'Safety & Compliance': '#EF4444',
    'Query Quality': '#8B5CF6',
    'Coding Readiness': '#F59E0B',
    'Stability': '#10B981',
    'Temporal Drift': '#EC4899',
    'Cross-Evidence': '#06B6D4',
};

export function AgentSignalsTimeline({
    data,
    height = 200,
}: AgentSignalsTimelineProps) {
    const timelineData = data || generateMockTimelineData();

    const chartData = useMemo(() => {
        return timelineData.map((point, index) => {
            const agentScores: Record<string, number> = {};
            Object.entries(point.agents).forEach(([agent, data]) => {
                // Convert risk level to score
                const riskScore =
                    data.risk_level === 'Critical' ? 4 :
                        data.risk_level === 'High' ? 3 :
                            data.risk_level === 'Medium' ? 2 : 1;
                agentScores[agent] = riskScore * data.confidence;
            });
            return {
                index,
                timestamp: new Date(point.timestamp).toLocaleTimeString([], {
                    hour: '2-digit',
                    minute: '2-digit'
                }),
                ...agentScores,
            };
        });
    }, [timelineData]);

    const agents = Object.keys(AGENT_COLORS);
    const maxScore = 4; // Max risk * max confidence

    return (
        <div className="signals-timeline">
            <h3 className="timeline-title">Agent Signals Over Time</h3>

            {/* Simple SVG chart */}
            <div className="chart-container" style={{ height }}>
                <svg viewBox={`0 0 100 ${height / 4}`} preserveAspectRatio="none" className="chart-svg">
                    {agents.map(agent => {
                        const points = chartData.map((d, i) => {
                            const x = (i / (chartData.length - 1)) * 100;
                            const y = height / 4 - ((d[agent] || 0) / maxScore) * (height / 4 - 10);
                            return `${x},${y}`;
                        }).join(' ');

                        return (
                            <polyline
                                key={agent}
                                fill="none"
                                stroke={AGENT_COLORS[agent]}
                                strokeWidth="1.5"
                                strokeLinecap="round"
                                strokeLinejoin="round"
                                points={points}
                                opacity="0.8"
                            />
                        );
                    })}
                </svg>

                {/* X-axis labels */}
                <div className="x-axis">
                    {chartData.filter((_, i) => i % 3 === 0).map((d, i) => (
                        <span key={i} className="x-label">{d.timestamp}</span>
                    ))}
                </div>
            </div>

            {/* Legend */}
            <div className="timeline-legend">
                {agents.map(agent => (
                    <span key={agent} className="legend-item">
                        <span
                            className="legend-color"
                            style={{ background: AGENT_COLORS[agent] }}
                        />
                        <span className="legend-text">{agent.split(' ')[0]}</span>
                    </span>
                ))}
            </div>

            <style>{`
                .signals-timeline {
                    background: rgba(255, 255, 255, 0.03);
                    border-radius: 12px;
                    padding: 20px;
                    border: 1px solid rgba(255, 255, 255, 0.1);
                }
                
                .timeline-title {
                    margin: 0 0 16px 0;
                    font-size: 16px;
                    font-weight: 600;
                    color: white;
                }
                
                .chart-container {
                    position: relative;
                    width: 100%;
                }
                
                .chart-svg {
                    width: 100%;
                    height: 100%;
                }
                
                .x-axis {
                    display: flex;
                    justify-content: space-between;
                    padding: 8px 0 0 0;
                }
                
                .x-label {
                    font-size: 10px;
                    color: rgba(255, 255, 255, 0.4);
                }
                
                .timeline-legend {
                    display: flex;
                    flex-wrap: wrap;
                    gap: 12px;
                    margin-top: 16px;
                    padding-top: 12px;
                    border-top: 1px solid rgba(255, 255, 255, 0.1);
                }
                
                .legend-item {
                    display: flex;
                    align-items: center;
                    gap: 4px;
                }
                
                .legend-color {
                    width: 10px;
                    height: 3px;
                    border-radius: 2px;
                }
                
                .legend-text {
                    font-size: 10px;
                    color: rgba(255, 255, 255, 0.6);
                }
            `}</style>
        </div>
    );
}

export default AgentSignalsTimeline;
