/**
 * Analytics Page - DQI Trends and Performance Metrics
 * ====================================================
 * Connected to LIVE API data from studies endpoint.
 * Shows real DQI distributions and performance metrics.
 */
import { useMemo } from 'react';
import { Link } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, BarChart, Bar, PieChart, Pie, Cell, Legend } from 'recharts';
import { studiesAPI } from '@/services/api';
import type { Study } from '@/types/api';

const RISK_COLORS = {
    Critical: '#ef4444',
    High: '#f97316',
    Medium: '#f59e0b',
    Low: '#22c55e',
    Unknown: '#94a3b8',
};

// Generate simulated trend data based on current study DQI scores
function generateTrendData(studies: Study[]) {
    const currentAvgDQI = studies.reduce((sum, s) => sum + (s.dqi_score || 0), 0) / (studies.length || 1);
    const months = ['Aug', 'Sep', 'Oct', 'Nov', 'Dec', 'Jan'];

    // Simulate historical data trending towards current value
    return months.map((month, i) => {
        const progressFactor = (i + 1) / months.length;
        const baseVariation = (Math.random() - 0.5) * 10;
        const startValue = currentAvgDQI - 15 + baseVariation;
        const currentValue = startValue + (currentAvgDQI - startValue) * progressFactor;

        return {
            month,
            avgDQI: Math.min(100, Math.max(0, currentValue)),
            safety: Math.min(100, Math.max(0, currentValue * 1.05 + (Math.random() - 0.5) * 8)),
            compliance: Math.min(100, Math.max(0, currentValue * 0.95 + (Math.random() - 0.5) * 8)),
            completeness: Math.min(100, Math.max(0, currentValue * 0.90 + (Math.random() - 0.5) * 8)),
        };
    });
}

export default function Analytics() {
    // Fetch studies with React Query
    const { data: studies = [], isLoading, isFetching, refetch } = useQuery({
        queryKey: ['studies'],
        queryFn: () => studiesAPI.getAll(),
        staleTime: 60000,
        refetchInterval: 60000, // Poll every minute
    });

    // Memoized calculations from real data
    const trendData = useMemo(() => generateTrendData(studies), [studies]);

    const riskDistribution = useMemo(() => {
        const dist = studies.reduce((acc, study) => {
            const risk = study.risk_level || 'Unknown';
            acc[risk] = (acc[risk] || 0) + 1;
            return acc;
        }, {} as Record<string, number>);

        return Object.entries(dist).map(([name, value]) => ({
            name,
            value,
            color: RISK_COLORS[name as keyof typeof RISK_COLORS] || RISK_COLORS.Unknown,
        }));
    }, [studies]);

    const dqiDistribution = useMemo(() => [
        { range: 'Critical (0-40)', count: studies.filter(s => (s.dqi_score || 0) < 40).length, color: '#ef4444' },
        { range: 'High (40-65)', count: studies.filter(s => (s.dqi_score || 0) >= 40 && (s.dqi_score || 0) < 65).length, color: '#f97316' },
        { range: 'Medium (65-85)', count: studies.filter(s => (s.dqi_score || 0) >= 65 && (s.dqi_score || 0) < 85).length, color: '#f59e0b' },
        { range: 'Low (85-100)', count: studies.filter(s => (s.dqi_score || 0) >= 85).length, color: '#22c55e' },
    ], [studies]);

    // Summary metrics
    const avgDQI = studies.length > 0
        ? (studies.reduce((sum, s) => sum + (s.dqi_score || 0), 0) / studies.length).toFixed(1)
        : '0';

    if (isLoading) {
        return (
            <div className="space-y-8 animate-pulse">
                <div className="h-8 bg-slate-200 dark:bg-slate-700 rounded w-1/4"></div>
                <div className="h-80 bg-slate-200 dark:bg-slate-700 rounded-xl"></div>
                <div className="grid grid-cols-2 gap-6">
                    <div className="h-64 bg-slate-200 dark:bg-slate-700 rounded-xl"></div>
                    <div className="h-64 bg-slate-200 dark:bg-slate-700 rounded-xl"></div>
                </div>
            </div>
        );
    }

    return (
        <div className="space-y-8">
            <header className="flex items-center justify-between">
                <div>
                    <h1 className="text-3xl font-bold text-slate-900 dark:text-white tracking-tight">Analytics Dashboard</h1>
                    <p className="text-slate-500 dark:text-slate-400 mt-2">
                        Performance trends and data quality metrics across your portfolio.
                        {isFetching && <span className="text-indigo-500 ml-2">Updating...</span>}
                    </p>
                </div>
                <div className="flex items-center gap-3">
                    <button
                        onClick={() => refetch()}
                        className="px-4 py-2 bg-slate-100 dark:bg-slate-700 text-slate-700 dark:text-slate-200 rounded-lg hover:bg-slate-200 dark:hover:bg-slate-600 transition-colors"
                    >
                        🔄 Refresh
                    </button>
                    <span className="px-3 py-1 bg-green-100 dark:bg-green-900/30 text-green-800 dark:text-green-400 text-sm rounded-full flex items-center gap-2">
                        <span className="w-2 h-2 bg-green-500 rounded-full animate-pulse"></span>
                        {studies.length} Studies
                    </span>
                </div>
            </header>

            {/* Key Metrics Summary */}
            <div className="grid grid-cols-1 md:grid-cols-5 gap-4">
                <div className="bg-gradient-to-br from-blue-500 to-blue-600 p-6 rounded-xl text-white">
                    <div className="text-sm font-medium opacity-80">Total Studies</div>
                    <div className="text-3xl font-bold mt-2">{studies.length}</div>
                </div>
                <div className="bg-gradient-to-br from-indigo-500 to-indigo-600 p-6 rounded-xl text-white">
                    <div className="text-sm font-medium opacity-80">Average DQI</div>
                    <div className="text-3xl font-bold mt-2">{avgDQI}</div>
                </div>
                <div className="bg-gradient-to-br from-green-500 to-green-600 p-6 rounded-xl text-white">
                    <div className="text-sm font-medium opacity-80">On Track (Low Risk)</div>
                    <div className="text-3xl font-bold mt-2">
                        {studies.filter(s => s.risk_level === 'Low').length}
                    </div>
                </div>
                <div className="bg-gradient-to-br from-amber-500 to-amber-600 p-6 rounded-xl text-white">
                    <div className="text-sm font-medium opacity-80">At Risk</div>
                    <div className="text-3xl font-bold mt-2">
                        {studies.filter(s => s.risk_level === 'Medium' || s.risk_level === 'High').length}
                    </div>
                </div>
                <div className="bg-gradient-to-br from-red-500 to-red-600 p-6 rounded-xl text-white">
                    <div className="text-sm font-medium opacity-80">Critical</div>
                    <div className="text-3xl font-bold mt-2">
                        {studies.filter(s => s.risk_level === 'Critical').length}
                    </div>
                </div>
            </div>

            {/* DQI Trend Chart */}
            <div className="bg-white dark:bg-slate-800 p-6 rounded-xl shadow-sm border border-slate-200 dark:border-slate-700">
                <div className="flex items-center justify-between mb-4">
                    <h2 className="text-lg font-semibold text-slate-900 dark:text-white">DQI Trend Over Time</h2>
                    <span className="text-xs text-slate-500 dark:text-slate-400">Simulated based on current scores</span>
                </div>
                <div className="h-80">
                    <ResponsiveContainer width="100%" height="100%">
                        <LineChart data={trendData}>
                            <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
                            <XAxis dataKey="month" stroke="#64748b" />
                            <YAxis domain={[0, 100]} stroke="#64748b" />
                            <Tooltip
                                contentStyle={{
                                    backgroundColor: '#1e293b',
                                    border: 'none',
                                    borderRadius: '8px',
                                    color: '#f1f5f9'
                                }}
                            />
                            <Legend />
                            <Line type="monotone" dataKey="avgDQI" stroke="#3b82f6" strokeWidth={3} name="Average DQI" dot={{ fill: '#3b82f6' }} />
                            <Line type="monotone" dataKey="safety" stroke="#ef4444" strokeWidth={2} name="Safety" />
                            <Line type="monotone" dataKey="compliance" stroke="#f59e0b" strokeWidth={2} name="Compliance" />
                            <Line type="monotone" dataKey="completeness" stroke="#22c55e" strokeWidth={2} name="Completeness" />
                        </LineChart>
                    </ResponsiveContainer>
                </div>
            </div>

            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                {/* Risk Distribution Pie Chart */}
                <div className="bg-white dark:bg-slate-800 p-6 rounded-xl shadow-sm border border-slate-200 dark:border-slate-700">
                    <h2 className="text-lg font-semibold text-slate-900 dark:text-white mb-4">Risk Distribution</h2>
                    <div className="h-64">
                        <ResponsiveContainer width="100%" height="100%">
                            <PieChart>
                                <Pie
                                    data={riskDistribution}
                                    cx="50%"
                                    cy="50%"
                                    innerRadius={60}
                                    outerRadius={100}
                                    paddingAngle={2}
                                    dataKey="value"
                                    label={({ name, value }) => value > 0 ? `${name}: ${value}` : ''}
                                >
                                    {riskDistribution.map((entry, index) => (
                                        <Cell key={`cell-${index}`} fill={entry.color} />
                                    ))}
                                </Pie>
                                <Tooltip />
                            </PieChart>
                        </ResponsiveContainer>
                    </div>
                </div>

                {/* DQI Score Distribution */}
                <div className="bg-white dark:bg-slate-800 p-6 rounded-xl shadow-sm border border-slate-200 dark:border-slate-700">
                    <h2 className="text-lg font-semibold text-slate-900 dark:text-white mb-4">DQI Score Distribution</h2>
                    <div className="h-64">
                        <ResponsiveContainer width="100%" height="100%">
                            <BarChart data={dqiDistribution}>
                                <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
                                <XAxis dataKey="range" stroke="#64748b" fontSize={12} />
                                <YAxis stroke="#64748b" />
                                <Tooltip
                                    contentStyle={{
                                        backgroundColor: '#1e293b',
                                        border: 'none',
                                        borderRadius: '8px',
                                        color: '#f1f5f9'
                                    }}
                                />
                                <Bar dataKey="count" name="Studies" radius={[4, 4, 0, 0]}>
                                    {dqiDistribution.map((entry, index) => (
                                        <Cell key={`cell-${index}`} fill={entry.color} />
                                    ))}
                                </Bar>
                            </BarChart>
                        </ResponsiveContainer>
                    </div>
                </div>
            </div>

            {/* Study Details Table */}
            <div className="bg-white dark:bg-slate-800 p-6 rounded-xl shadow-sm border border-slate-200 dark:border-slate-700">
                <h2 className="text-lg font-semibold text-slate-900 dark:text-white mb-4">Study Performance Details</h2>
                <div className="overflow-x-auto">
                    <table className="w-full">
                        <thead>
                            <tr className="text-left border-b border-slate-200 dark:border-slate-700">
                                <th className="pb-3 text-sm font-medium text-slate-500 dark:text-slate-400">Study</th>
                                <th className="pb-3 text-sm font-medium text-slate-500 dark:text-slate-400">DQI Score</th>
                                <th className="pb-3 text-sm font-medium text-slate-500 dark:text-slate-400">Risk Level</th>
                                <th className="pb-3 text-sm font-medium text-slate-500 dark:text-slate-400">Enrollment</th>
                                <th className="pb-3 text-sm font-medium text-slate-500 dark:text-slate-400">Actions</th>
                            </tr>
                        </thead>
                        <tbody>
                            {studies.slice(0, 10).map(study => (
                                <tr key={study.study_id} className="border-b border-slate-100 dark:border-slate-700/50">
                                    <td className="py-3 font-medium text-slate-900 dark:text-white">{study.study_name}</td>
                                    <td className="py-3">
                                        <span className="font-semibold text-slate-900 dark:text-white">
                                            {study.dqi_score?.toFixed(1) || 'N/A'}
                                        </span>
                                    </td>
                                    <td className="py-3">
                                        <span className={`px-2 py-1 rounded-full text-xs font-medium ${study.risk_level === 'Critical' ? 'bg-red-100 text-red-800 dark:bg-red-900/30 dark:text-red-400' :
                                                study.risk_level === 'High' ? 'bg-orange-100 text-orange-800 dark:bg-orange-900/30 dark:text-orange-400' :
                                                    study.risk_level === 'Medium' ? 'bg-amber-100 text-amber-800 dark:bg-amber-900/30 dark:text-amber-400' :
                                                        'bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-400'
                                            }`}>
                                            {study.risk_level || 'Unknown'}
                                        </span>
                                    </td>
                                    <td className="py-3 text-slate-600 dark:text-slate-400">
                                        {study.enrollment_percentage?.toFixed(0) || 0}%
                                    </td>
                                    <td className="py-3">
                                        <Link 
                                            to={`/insights/${study.study_id}`}
                                            className="inline-flex items-center gap-1 text-sm text-indigo-600 dark:text-indigo-400 hover:text-indigo-700 dark:hover:text-indigo-300 font-medium"
                                        >
                                            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z" />
                                            </svg>
                                            AI Insights
                                        </Link>
                                    </td>
                                </tr>
                            ))}
                        </tbody>
                    </table>
                </div>
            </div>
        </div>
    );
}
