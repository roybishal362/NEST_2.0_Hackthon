// Risk Heatmap Component
// ========================================
import type { Study } from '@/types/api';

interface RiskHeatmapProps {
    studies: Study[];
}

export function RiskHeatmap({ studies }: RiskHeatmapProps) {
    // Group studies by risk level
    const riskGroups = {
        Critical: studies.filter(s => s.risk_level === 'Critical'),
        High: studies.filter(s => s.risk_level === 'High'),
        Medium: studies.filter(s => s.risk_level === 'Medium'),
        Low: studies.filter(s => s.risk_level === 'Low'),
        Unknown: studies.filter(s => !s.risk_level || s.risk_level === 'Unknown'),
    };

    const riskColors = {
        Critical: 'bg-red-500',
        High: 'bg-orange-500',
        Medium: 'bg-amber-500',
        Low: 'bg-green-500',
        Unknown: 'bg-slate-400',
    };

    const riskBgColors = {
        Critical: 'bg-red-500/10 border-red-500/30',
        High: 'bg-orange-500/10 border-orange-500/30',
        Medium: 'bg-amber-500/10 border-amber-500/30',
        Low: 'bg-green-500/10 border-green-500/30',
        Unknown: 'bg-slate-500/10 border-slate-500/30',
    };

    return (
        <div className="space-y-4">
            {Object.entries(riskGroups).map(([level, levelStudies]) => (
                levelStudies.length > 0 && (
                    <div key={level} className={`p-4 rounded-lg border ${riskBgColors[level as keyof typeof riskBgColors]}`}>
                        <div className="flex items-center gap-2 mb-3">
                            <span className={`w-3 h-3 rounded-full ${riskColors[level as keyof typeof riskColors]}`}></span>
                            <span className="font-medium text-sm text-slate-800 dark:text-white">{level}</span>
                            <span className="text-xs text-slate-600 dark:text-slate-300">({levelStudies.length})</span>
                        </div>
                        <div className="flex flex-wrap gap-2">
                            {levelStudies.map(study => (
                                <div
                                    key={study.study_id}
                                    className={`px-3 py-1.5 rounded-md text-xs font-medium ${riskColors[level as keyof typeof riskColors]} text-white cursor-pointer hover:opacity-80 transition-opacity`}
                                    title={`${study.study_id}: DQI ${study.dqi_score || 'N/A'}`}
                                >
                                    {study.study_id.replace('STUDY_', 'S')}
                                </div>
                            ))}
                        </div>
                    </div>
                )
            ))}
        </div>
    );
}

export default RiskHeatmap;
