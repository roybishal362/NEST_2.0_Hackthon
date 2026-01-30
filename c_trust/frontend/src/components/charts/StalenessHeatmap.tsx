/**
 * Staleness Heatmap
 * ==================
 * Grid visualization showing data freshness across entities.
 * Based on Guardian Agent's staleness checks.
 */

import { useMemo } from 'react';

interface StalenessData {
    entity_id: string;
    entity_type: string;
    days_stale: number;
    last_updated: string;
    status: 'fresh' | 'stale' | 'critical';
}

interface StalenessHeatmapProps {
    data?: StalenessData[];
    title?: string;
    showLegend?: boolean;
}

// Mock data generator for demo
function generateMockData(): StalenessData[] {
    const entityTypes = ['Subject', 'Visit', 'Form', 'Query'];
    const entities: StalenessData[] = [];

    for (let i = 0; i < 24; i++) {
        const daysStale = Math.random() * 14;
        entities.push({
            entity_id: `ENT-${String(i + 1).padStart(3, '0')}`,
            entity_type: entityTypes[i % 4],
            days_stale: Math.round(daysStale * 10) / 10,
            last_updated: new Date(Date.now() - daysStale * 86400000).toISOString(),
            status: daysStale < 2 ? 'fresh' : daysStale < 7 ? 'stale' : 'critical',
        });
    }

    return entities;
}

export function StalenessHeatmap({
    data,
    title = 'Data Staleness Heatmap',
    showLegend = true,
}: StalenessHeatmapProps) {
    const entities = data || generateMockData();

    // Group by entity type
    const grouped = useMemo(() => {
        const groups: Record<string, StalenessData[]> = {};
        entities.forEach(e => {
            if (!groups[e.entity_type]) groups[e.entity_type] = [];
            groups[e.entity_type].push(e);
        });
        return groups;
    }, [entities]);

    const getColor = (days: number) => {
        if (days < 1) return '#10B981';  // Fresh - green
        if (days < 3) return '#84CC16';  // Recent - lime
        if (days < 5) return '#EAB308';  // Warning - yellow
        if (days < 7) return '#F59E0B';  // Stale - amber
        if (days < 10) return '#EF4444'; // Critical - red
        return '#991B1B';                 // Very stale - dark red
    };

    return (
        <div className="staleness-heatmap">
            <h3 className="heatmap-title">{title}</h3>

            <div className="heatmap-grid">
                {Object.entries(grouped).map(([type, items]) => (
                    <div key={type} className="heatmap-row">
                        <div className="row-label">{type}</div>
                        <div className="row-cells">
                            {items.map(item => (
                                <div
                                    key={item.entity_id}
                                    className="heatmap-cell"
                                    style={{ background: getColor(item.days_stale) }}
                                    title={`${item.entity_id}: ${item.days_stale}d stale`}
                                >
                                    <span className="cell-value">
                                        {item.days_stale < 1 ? '<1' : Math.round(item.days_stale)}
                                    </span>
                                </div>
                            ))}
                        </div>
                    </div>
                ))}
            </div>

            {showLegend && (
                <div className="heatmap-legend">
                    <span className="legend-item">
                        <span className="legend-color" style={{ background: '#10B981' }} />
                        Fresh (&lt;1d)
                    </span>
                    <span className="legend-item">
                        <span className="legend-color" style={{ background: '#EAB308' }} />
                        Warning (3-5d)
                    </span>
                    <span className="legend-item">
                        <span className="legend-color" style={{ background: '#EF4444' }} />
                        Stale (&gt;7d)
                    </span>
                </div>
            )}

            <style>{`
                .staleness-heatmap {
                    background: rgba(255, 255, 255, 0.03);
                    border-radius: 12px;
                    padding: 20px;
                    border: 1px solid rgba(255, 255, 255, 0.1);
                }
                
                .heatmap-title {
                    margin: 0 0 16px 0;
                    font-size: 16px;
                    font-weight: 600;
                    color: white;
                }
                
                .heatmap-grid {
                    display: flex;
                    flex-direction: column;
                    gap: 8px;
                }
                
                .heatmap-row {
                    display: flex;
                    align-items: center;
                    gap: 12px;
                }
                
                .row-label {
                    width: 80px;
                    font-size: 12px;
                    color: rgba(255, 255, 255, 0.7);
                    text-align: right;
                }
                
                .row-cells {
                    display: flex;
                    gap: 4px;
                    flex-wrap: wrap;
                }
                
                .heatmap-cell {
                    width: 36px;
                    height: 36px;
                    border-radius: 4px;
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    cursor: pointer;
                    transition: transform 0.15s;
                }
                
                .heatmap-cell:hover {
                    transform: scale(1.1);
                    z-index: 1;
                }
                
                .cell-value {
                    font-size: 10px;
                    font-weight: 600;
                    color: rgba(0, 0, 0, 0.7);
                }
                
                .heatmap-legend {
                    display: flex;
                    gap: 16px;
                    margin-top: 16px;
                    padding-top: 12px;
                    border-top: 1px solid rgba(255, 255, 255, 0.1);
                }
                
                .legend-item {
                    display: flex;
                    align-items: center;
                    gap: 6px;
                    font-size: 11px;
                    color: rgba(255, 255, 255, 0.6);
                }
                
                .legend-color {
                    width: 12px;
                    height: 12px;
                    border-radius: 2px;
                }
            `}</style>
        </div>
    );
}

export default StalenessHeatmap;
