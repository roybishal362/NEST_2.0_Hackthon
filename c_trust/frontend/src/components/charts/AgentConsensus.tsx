// Agent Consensus Visualization Component
// ========================================

interface AgentSignal {
    name: string;
    signal: 'positive' | 'negative' | 'neutral';
    confidence: number;
    weight: number;
}

interface AgentConsensusProps {
    signals?: AgentSignal[];
}

const defaultSignals: AgentSignal[] = [
    { name: 'Completeness', signal: 'positive', confidence: 0.92, weight: 1.5 },
    { name: 'Safety', signal: 'negative', confidence: 0.88, weight: 3.0 },
    { name: 'Query', signal: 'neutral', confidence: 0.95, weight: 1.5 },
    { name: 'Coding', signal: 'positive', confidence: 0.90, weight: 1.2 },
    { name: 'Stability', signal: 'positive', confidence: 0.85, weight: -1.5 },
];

export function AgentConsensus({ signals = defaultSignals }: AgentConsensusProps) {
    const getSignalColor = (signal: string) => {
        switch (signal) {
            case 'positive': return 'bg-green-500';
            case 'negative': return 'bg-red-500';
            default: return 'bg-amber-500';
        }
    };

    const getSignalIcon = (signal: string) => {
        switch (signal) {
            case 'positive': return '↑';
            case 'negative': return '↓';
            default: return '→';
        }
    };

    // Calculate weighted consensus
    const totalWeight = signals.reduce((sum, s) => sum + Math.abs(s.weight), 0);
    const weightedScore = signals.reduce((sum, s) => {
        const signalValue = s.signal === 'positive' ? 1 : s.signal === 'negative' ? -1 : 0;
        return sum + (signalValue * s.confidence * Math.abs(s.weight));
    }, 0);
    const consensusScore = ((weightedScore / totalWeight) + 1) / 2 * 100; // Normalize to 0-100

    return (
        <div className="space-y-4">
            {/* Consensus Score */}
            <div className="flex items-center justify-between p-3 bg-slate-100 dark:bg-slate-700/50 rounded-lg">
                <span className="text-sm font-medium text-slate-800 dark:text-white">Consensus Score</span>
                <span className={`text-lg font-bold ${
                    consensusScore >= 60 ? 'text-green-500' : 
                    consensusScore >= 40 ? 'text-amber-500' : 'text-red-500'
                }`}>
                    {consensusScore.toFixed(0)}%
                </span>
            </div>

            {/* Agent Signals */}
            <div className="space-y-2">
                {signals.map((agent) => (
                    <div key={agent.name} className="flex items-center gap-3">
                        <div className={`w-6 h-6 rounded-full ${getSignalColor(agent.signal)} flex items-center justify-center text-white text-xs font-bold`}>
                            {getSignalIcon(agent.signal)}
                        </div>
                        <div className="flex-1">
                            <div className="flex items-center justify-between">
                                <span className="text-sm font-medium text-slate-800 dark:text-white">{agent.name}</span>
                                <span className="text-xs text-slate-600 dark:text-slate-300">
                                    {(agent.confidence * 100).toFixed(0)}% conf
                                </span>
                            </div>
                            <div className="w-full bg-slate-200 dark:bg-slate-600 rounded-full h-1.5 mt-1">
                                <div 
                                    className={`h-full rounded-full ${getSignalColor(agent.signal)}`}
                                    style={{ width: `${agent.confidence * 100}%` }}
                                />
                            </div>
                        </div>
                        <span className="text-xs text-slate-600 dark:text-slate-300 w-8 text-right">
                            {agent.weight > 0 ? '+' : ''}{agent.weight}x
                        </span>
                    </div>
                ))}
            </div>
        </div>
    );
}

export default AgentConsensus;
