import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts';
import { studiesAPI } from '@/services/api';
import { getRiskColor, getRiskLabel, formatPercentage, formatDQI } from '@/lib/utils';
import { DQIGauge } from '@/components/charts/DQIGauge';
import { RiskHeatmap } from '@/components/charts/RiskHeatmap';
import { AgentConsensus } from '@/components/charts/AgentConsensus';
import { ExportButton } from '@/components/ui/ExportButton';
import type { Study, DashboardSummary } from '@/types/api';

// Mock trend data for demonstration
const generateTrendData = () => {
    const days = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'];
    return days.map((day, i) => ({
        day,
        dqi: 72 + Math.random() * 10 + i * 0.5,
    }));
};

// Metric Card Component
function MetricCard({ title, value, subtext, color = "blue", icon }: { 
    title: string, 
    value: string | number, 
    subtext: string, 
    color?: string,
    icon?: React.ReactNode 
}) {
    const colorClasses: Record<string, string> = {
        blue: "from-blue-500 to-blue-600",
        green: "from-green-500 to-green-600",
        red: "from-red-500 to-red-600",
        amber: "from-amber-500 to-amber-600",
        purple: "from-purple-500 to-purple-600",
        indigo: "from-indigo-500 to-indigo-600",
    };

    return (
        <div className={`p-6 rounded-xl bg-gradient-to-br ${colorClasses[color] || colorClasses.blue} text-white shadow-lg`}>
            <div className="flex items-start justify-between">
                <div>
                    <div className="text-sm font-medium opacity-80 uppercase tracking-wide">{title}</div>
                    <div className="mt-2 text-3xl font-bold">{value}</div>
                    <div className="mt-1 text-sm opacity-70">{subtext}</div>
                </div>
                {icon && <div className="text-white/50">{icon}</div>}
            </div>
        </div>
    );
}

// Alert Card Component
function AlertCard({ severity, title, study, time }: { severity: string, title: string, study: string, time: string }) {
    const severityStyles: Record<string, { bg: string, icon: string }> = {
        critical: { bg: 'bg-red-500/10 border-red-500/30', icon: '🚨' },
        high: { bg: 'bg-orange-500/10 border-orange-500/30', icon: '⚠️' },
        medium: { bg: 'bg-amber-500/10 border-amber-500/30', icon: '📋' },
        low: { bg: 'bg-blue-500/10 border-blue-500/30', icon: 'ℹ️' },
    };
    
    const style = severityStyles[severity] || severityStyles.low;
    
    return (
        <div className={`p-3 rounded-lg border ${style.bg} flex items-start gap-3`}>
            <span className="text-lg">{style.icon}</span>
            <div className="flex-1 min-w-0">
                <p className="text-sm font-medium text-slate-800 dark:text-white truncate">{title}</p>
                <p className="text-xs text-slate-600 dark:text-slate-300">{study} • {time}</p>
            </div>
        </div>
    );
}

// Study Card Component
function StudyCard({ study }: { study: Study }) {
    const riskColor = getRiskColor(study.risk_level);
    const riskLabel = getRiskLabel(study.risk_level);

    return (
        <div className={`
            relative h-full p-5 rounded-xl border border-transparent 
            transition-all duration-300 hover:scale-105 hover:shadow-xl hover:z-10
            bg-white dark:bg-slate-800 shadow-sm ring-1 ring-slate-900/5 dark:ring-slate-700
            group
        `}>
            <div className={`absolute top-0 right-0 px-3 py-1 rounded-bl-xl rounded-tr-xl text-xs font-bold text-white uppercase tracking-wider ${riskColor}`}>
                {riskLabel}
            </div>

            <Link to={`/studies/${study.study_id}`} className="block">
                <div className="mt-2">
                    <h3 className="text-xl font-bold text-slate-900 dark:text-white group-hover:text-indigo-600 dark:group-hover:text-indigo-400 transition-colors">
                        {study.study_id}
                    </h3>
                    <div className="text-xs text-slate-500 dark:text-slate-400 font-medium">{study.study_name || "Protocol " + study.study_id}</div>
                </div>

                <div className="mt-6 space-y-3">
                    <div className="flex items-center justify-between text-sm">
                        <span className="text-slate-500 dark:text-slate-400">DQI Score</span>
                        <span className={`font-bold ${study.dqi_score && study.dqi_score > 80 ? 'text-green-600' : 'text-amber-600'}`}>
                            {formatDQI(study.dqi_score)}
                        </span>
                    </div>
                    <div className="w-full bg-slate-100 dark:bg-slate-700 rounded-full h-1.5 overflow-hidden">
                        <div
                            className={`h-full rounded-full ${study.dqi_score && study.dqi_score > 80 ? 'bg-green-500' : 'bg-amber-500'}`}
                            style={{ width: `${study.dqi_score || 0}%` }}
                        />
                    </div>

                    <div className="flex items-center justify-between text-sm pt-2 border-t border-slate-100 dark:border-slate-700">
                        <span className="text-slate-500 dark:text-slate-400">Enrollment</span>
                        <span className="text-slate-700 dark:text-slate-300 font-medium">{formatPercentage(study.enrollment_percentage)}</span>
                    </div>
                </div>
            </Link>

            {/* AI Insights Link */}
            <div className="mt-4 pt-3 border-t border-slate-100 dark:border-slate-700">
                <Link 
                    to={`/insights/${study.study_id}`}
                    className="flex items-center justify-center gap-2 w-full px-3 py-2 text-sm font-medium text-indigo-600 dark:text-indigo-400 hover:text-indigo-700 dark:hover:text-indigo-300 hover:bg-indigo-50 dark:hover:bg-indigo-900/20 rounded-lg transition-colors"
                    onClick={(e) => e.stopPropagation()}
                >
                    <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z" />
                    </svg>
                    AI Insights
                </Link>
            </div>
        </div>
    );
}

export default function Portfolio() {
    const [studies, setStudies] = useState<Study[]>([]);
    const [summary, setSummary] = useState<DashboardSummary | null>(null);
    const [loading, setLoading] = useState(true);
    const [trendData] = useState(generateTrendData());

    useEffect(() => {
        async function loadData() {
            try {
                const [studiesData, summaryData] = await Promise.all([
                    studiesAPI.getAll(),
                    studiesAPI.getDashboardSummary()
                ]);
                setStudies(studiesData);
                setSummary(summaryData);
            } catch (err) {
                console.error('Failed to load dashboard:', err);
            } finally {
                setLoading(false);
            }
        }
        loadData();
    }, []);

    if (loading) {
        return (
            <div className="space-y-6">
                <div className="h-8 w-48 bg-slate-200 dark:bg-slate-700 rounded animate-pulse"></div>
                <div className="grid grid-cols-4 gap-6">
                    {[1, 2, 3, 4].map(i => (
                        <div key={i} className="h-32 bg-slate-200 dark:bg-slate-700 rounded-xl animate-pulse"></div>
                    ))}
                </div>
            </div>
        );
    }

    const avgDQI = summary?.avg_dqi || 0;

    return (
        <div className="space-y-8">
            <header className="flex items-center justify-between">
                <div>
                    <h1 className="text-3xl font-bold text-slate-900 dark:text-white tracking-tight">Portfolio Overview</h1>
                    <p className="text-slate-500 dark:text-slate-400 mt-2">Executive summary of clinical program performance.</p>
                </div>
                <div className="flex gap-3">
                    <ExportButton />
                </div>
            </header>

            {/* Executive Summary Cards */}
            {summary && (
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
                    <MetricCard
                        title="Average DQI"
                        value={summary.avg_dqi.toFixed(1)}
                        subtext="Target: >85.0"
                        color={summary.avg_dqi > 80 ? "green" : "amber"}
                    />
                    <MetricCard
                        title="Critical Studies"
                        value={summary.critical_risks}
                        subtext="Requires immediate attention"
                        color={summary.critical_risks > 0 ? "red" : "green"}
                    />
                    <MetricCard
                        title="Sites at Risk"
                        value={summary.sites_at_risk}
                        subtext={`Across ${summary.total_studies} studies`}
                        color="purple"
                    />
                    <MetricCard
                        title="Total Patients"
                        value={summary.total_patients.toLocaleString()}
                        subtext="Enrolled to date"
                        color="blue"
                    />
                </div>
            )}

            {/* Main Dashboard Grid */}
            <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
                {/* DQI Gauge and Trend */}
                <div className="lg:col-span-2 bg-white dark:bg-slate-800 p-6 rounded-xl shadow-sm border border-slate-200 dark:border-slate-700">
                    <h2 className="text-lg font-semibold text-slate-900 dark:text-white mb-4">Portfolio DQI Performance</h2>
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                        <div className="flex flex-col items-center justify-center">
                            <DQIGauge score={avgDQI} size="lg" />
                            <p className="mt-4 text-sm text-slate-500 dark:text-slate-400">Portfolio Average</p>
                        </div>
                        <div className="h-48">
                            <ResponsiveContainer width="100%" height="100%">
                                <LineChart data={trendData}>
                                    <CartesianGrid strokeDasharray="3 3" stroke="#374151" opacity={0.3} />
                                    <XAxis dataKey="day" stroke="#6b7280" fontSize={12} />
                                    <YAxis domain={[60, 100]} stroke="#6b7280" fontSize={12} />
                                    <Tooltip 
                                        contentStyle={{ 
                                            backgroundColor: '#1e293b', 
                                            border: 'none', 
                                            borderRadius: '8px',
                                            color: '#f1f5f9'
                                        }} 
                                    />
                                    <Line 
                                        type="monotone" 
                                        dataKey="dqi" 
                                        stroke="#6366f1" 
                                        strokeWidth={3}
                                        dot={{ fill: '#6366f1', strokeWidth: 2 }}
                                    />
                                </LineChart>
                            </ResponsiveContainer>
                            <p className="text-center text-xs text-slate-500 dark:text-slate-400 mt-2">7-Day Trend</p>
                        </div>
                    </div>
                </div>

                {/* Real-time Alerts */}
                <div className="bg-white dark:bg-slate-800 p-6 rounded-xl shadow-sm border border-slate-200 dark:border-slate-700">
                    <div className="flex items-center justify-between mb-4">
                        <h2 className="text-lg font-semibold text-slate-900 dark:text-white">Active Alerts</h2>
                        <Link to="/notifications" className="text-sm text-indigo-500 hover:text-indigo-600">View all</Link>
                    </div>
                    <div className="space-y-3">
                        <AlertCard severity="critical" title="SAE Review Overdue" study="STUDY_08" time="10 min ago" />
                        <AlertCard severity="high" title="Data Entry Lag" study="STUDY_05" time="1 hour ago" />
                        <AlertCard severity="medium" title="Query Backlog" study="STUDY_02" time="2 hours ago" />
                    </div>
                </div>
            </div>

            {/* Risk Heatmap and Agent Consensus */}
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                <div className="bg-white dark:bg-slate-800 p-6 rounded-xl shadow-sm border border-slate-200 dark:border-slate-700">
                    <h2 className="text-lg font-semibold text-slate-900 dark:text-white mb-4">Risk Heatmap</h2>
                    <RiskHeatmap studies={studies} />
                </div>
                <div className="bg-white dark:bg-slate-800 p-6 rounded-xl shadow-sm border border-slate-200 dark:border-slate-700">
                    <h2 className="text-lg font-semibold text-slate-900 dark:text-white mb-4">Agent Consensus</h2>
                    <AgentConsensus />
                </div>
            </div>

            {/* Study Grid */}
            <section>
                <div className="flex items-center justify-between mb-6">
                    <h2 className="text-xl font-bold text-slate-800 dark:text-white">Active Studies</h2>
                    <div className="flex gap-2 text-sm">
                        <span className="px-3 py-1 bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-full text-slate-600 dark:text-slate-300 shadow-sm cursor-pointer hover:bg-slate-50 dark:hover:bg-slate-700">Sort by: Risk</span>
                        <span className="px-3 py-1 bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-full text-slate-600 dark:text-slate-300 shadow-sm cursor-pointer hover:bg-slate-50 dark:hover:bg-slate-700">Filter: All</span>
                    </div>
                </div>

                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-6">
                    {studies.map((study) => (
                        <StudyCard key={study.study_id} study={study} />
                    ))}
                </div>
            </section>
        </div>
    );
}
