// Study Dashboard - Detailed Study View with Drill-Down
// ========================================
import { useEffect, useState, useMemo } from 'react';
import { useParams, useNavigate, useSearchParams } from 'react-router-dom';
import {
    useReactTable,
    getCoreRowModel,
    getSortedRowModel,
    getFilteredRowModel,
    flexRender,
    type ColumnDef,
    type SortingState,
    type ColumnFiltersState,
} from '@tanstack/react-table';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, RadarChart, PolarGrid, PolarAngleAxis, PolarRadiusAxis, Radar } from 'recharts';
import { studiesAPI } from '@/services/api';
import { formatDQI, getRiskColor, getRiskLabel, getDQIBandColor, getDQIBandLabel, cn } from '@/lib/utils';
import type { Study, SiteSummary } from '@/types/api';
import { PipelineStatusCard } from '@/components/PipelineStatusCard';
import { AgentOrchestrationPanel } from '@/components/AgentOrchestrationPanel';

// DQI Dimension breakdown mock data
const generateDimensionData = (dqi: number) => [
    { dimension: 'Safety', score: Math.min(100, dqi + Math.random() * 15 - 5), weight: 35 },
    { dimension: 'Compliance', score: Math.min(100, dqi + Math.random() * 20 - 10), weight: 25 },
    { dimension: 'Completeness', score: Math.min(100, dqi + Math.random() * 25 - 12), weight: 20 },
    { dimension: 'Operations', score: Math.min(100, dqi + Math.random() * 18 - 8), weight: 15 },
    { dimension: 'Timeliness', score: Math.min(100, dqi + Math.random() * 22 - 11), weight: 5 },
];

// DQI trend mock data
const generateTrendData = (baseDqi: number) => {
    const weeks = ['W1', 'W2', 'W3', 'W4', 'W5', 'W6'];
    return weeks.map((week, i) => ({
        week,
        dqi: Math.max(0, Math.min(100, baseDqi - 10 + i * 3 + Math.random() * 8 - 4)),
    }));
};

type TabType = 'overview' | 'sites' | 'dqi' | 'agents';

export default function StudyDashboard() {
    const { id } = useParams<{ id: string }>();
    const navigate = useNavigate();
    const [searchParams, setSearchParams] = useSearchParams();

    const [study, setStudy] = useState<Study | null>(null);
    const [loading, setLoading] = useState(true);

    // Preserve tab state in URL for context preservation
    const activeTab = (searchParams.get('tab') as TabType) || 'overview';
    const setActiveTab = (tab: TabType) => {
        setSearchParams({ tab });
    };

    // Table state
    const [sorting, setSorting] = useState<SortingState>([]);
    const [columnFilters, setColumnFilters] = useState<ColumnFiltersState>([]);
    const [globalFilter, setGlobalFilter] = useState('');

    useEffect(() => {
        if (id) {
            studiesAPI.getById(id)
                .then(setStudy)
                .catch(console.error)
                .finally(() => setLoading(false));
        }
    }, [id]);

    // TanStack Table columns for sites
    const columns = useMemo<ColumnDef<SiteSummary>[]>(() => [
        {
            accessorKey: 'site_id',
            header: 'Site ID',
            cell: ({ row }) => (
                <button
                    onClick={() => navigate(`/studies/${id}/sites/${row.original.site_id}?from=${id}`)}
                    className="font-medium text-indigo-600 hover:text-indigo-800 dark:text-indigo-400"
                >
                    {row.original.site_id}
                </button>
            ),
        },
        {
            accessorKey: 'risk_level',
            header: 'Risk Level',
            cell: ({ row }) => (
                <span className={cn(
                    'px-2 py-1 text-xs font-semibold rounded-full text-white',
                    getRiskColor(row.original.risk_level)
                )}>
                    {row.original.risk_level}
                </span>
            ),
            filterFn: (row, id, value) => {
                return value.includes(row.getValue(id));
            },
        },
        {
            accessorKey: 'enrollment',
            header: () => <div className="text-right">Patients</div>,
            cell: ({ row }) => <div className="text-right">{row.original.enrollment}</div>,
        },
        {
            accessorKey: 'saes',
            header: () => <div className="text-right">SAEs</div>,
            cell: ({ row }) => (
                <div className={cn(
                    'text-right font-medium',
                    row.original.saes > 0 ? 'text-red-600' : 'text-slate-500'
                )}>
                    {row.original.saes}
                </div>
            ),
        },
        {
            accessorKey: 'queries',
            header: () => <div className="text-right">Open Queries</div>,
            cell: ({ row }) => (
                <div className={cn(
                    'text-right',
                    row.original.queries > 10 ? 'text-amber-600 font-medium' : 'text-slate-500'
                )}>
                    {row.original.queries}
                </div>
            ),
        },
        {
            id: 'actions',
            header: () => <div className="text-right">Action</div>,
            cell: ({ row }) => (
                <div className="text-right">
                    <button
                        onClick={() => navigate(`/studies/${id}/sites/${row.original.site_id}?from=${id}`)}
                        className="text-indigo-600 hover:text-indigo-900 dark:text-indigo-400 text-sm font-medium"
                    >
                        View Details →
                    </button>
                </div>
            ),
        },
    ], [id, navigate]);

    const table = useReactTable({
        data: study?.sites || [],
        columns,
        state: { sorting, columnFilters, globalFilter },
        onSortingChange: setSorting,
        onColumnFiltersChange: setColumnFilters,
        onGlobalFilterChange: setGlobalFilter,
        getCoreRowModel: getCoreRowModel(),
        getSortedRowModel: getSortedRowModel(),
        getFilteredRowModel: getFilteredRowModel(),
    });

    if (loading) {
        return (
            <div className="space-y-6 animate-pulse">
                <div className="h-32 bg-slate-200 dark:bg-slate-700 rounded-xl"></div>
                <div className="h-12 bg-slate-200 dark:bg-slate-700 rounded-lg w-1/3"></div>
                <div className="h-96 bg-slate-200 dark:bg-slate-700 rounded-xl"></div>
            </div>
        );
    }

    if (!study) {
        return (
            <div className="p-12 text-center">
                <div className="text-6xl mb-4">🔍</div>
                <h2 className="text-xl font-semibold text-slate-900 dark:text-white">Study Not Found</h2>
                <p className="text-slate-500 mt-2">The requested study could not be loaded.</p>
                <button
                    onClick={() => navigate('/portfolio')}
                    className="mt-4 px-4 py-2 bg-indigo-600 text-white rounded-lg hover:bg-indigo-700"
                >
                    Back to Portfolio
                </button>
            </div>
        );
    }

    const riskColor = getRiskColor(study.risk_level);
    const riskLabel = getRiskLabel(study.risk_level);
    const dimensionData = generateDimensionData(study.dqi_score || 70);
    const trendData = generateTrendData(study.dqi_score || 70);

    return (
        <div className="space-y-8">
            {/* Header */}
            <div className="bg-white dark:bg-slate-800 p-6 rounded-xl shadow-sm border border-slate-200 dark:border-slate-700 flex justify-between items-start">
                <div>
                    <div className="flex items-center gap-3 mb-2">
                        <h1 className="text-3xl font-bold text-slate-900 dark:text-white">{study.study_id}</h1>
                        <span className={cn('px-3 py-1 rounded-full text-xs font-bold uppercase text-white', riskColor)}>
                            {riskLabel}
                        </span>
                    </div>
                    <div className="text-slate-500 dark:text-slate-400 font-medium">
                        {study.study_name || `Protocol ${study.study_id}`}
                    </div>
                    <div className="mt-4 flex gap-6 text-sm">
                        <div>
                            <span className="block text-slate-400 text-xs uppercase tracking-wider">Phase</span>
                            <span className="font-semibold text-slate-700 dark:text-slate-300">
                                {study.timeline?.phase || 'Phase 2'}
                            </span>
                        </div>
                        <div>
                            <span className="block text-slate-400 text-xs uppercase tracking-wider">Status</span>
                            <span className="font-semibold text-slate-700 dark:text-slate-300">
                                {study.timeline?.status || 'Ongoing'}
                            </span>
                        </div>
                        <div>
                            <span className="block text-slate-400 text-xs uppercase tracking-wider">Last Refresh</span>
                            <span className="font-semibold text-slate-700 dark:text-slate-300">
                                {study.last_refresh ? new Date(study.last_refresh).toLocaleDateString() : 'Just now'}
                            </span>
                        </div>
                    </div>
                </div>
                <div className="text-right">
                    <div className="text-4xl font-bold text-slate-900 dark:text-white">{formatDQI(study.dqi_score)}</div>
                    <div className="text-sm text-slate-500 dark:text-slate-400 font-medium">Overall DQI Score</div>
                    <div className={cn('mt-2 inline-block px-2 py-1 rounded text-xs font-medium text-white', getDQIBandColor(study.dqi_score))}>
                        {getDQIBandLabel(study.dqi_score)} Band
                    </div>
                    <div className="mt-4">
                        <button
                            onClick={() => navigate(`/insights/${study.study_id}`)}
                            className="px-4 py-2 bg-blue-600 text-white text-sm font-medium rounded-lg hover:bg-blue-700 transition-colors"
                        >
                            View AI Insights
                        </button>
                    </div>
                </div>
            </div>

            {/* Tabs */}
            <div className="border-b border-slate-200 dark:border-slate-700">
                <nav className="-mb-px flex space-x-8">
                    {(['overview', 'sites', 'dqi', 'agents'] as TabType[]).map((tab) => (
                        <button
                            key={tab}
                            onClick={() => setActiveTab(tab)}
                            className={cn(
                                'py-4 px-1 border-b-2 font-medium text-sm transition-colors',
                                activeTab === tab
                                    ? 'border-indigo-500 text-indigo-600 dark:text-indigo-400'
                                    : 'border-transparent text-slate-500 hover:text-slate-700 hover:border-slate-300 dark:hover:text-slate-300'
                            )}
                        >
                            {tab === 'dqi' ? 'DQI Analysis' : tab === 'agents' ? 'Agent Signals' : tab.charAt(0).toUpperCase() + tab.slice(1)}
                        </button>
                    ))}
                </nav>
            </div>

            {/* Content */}
            <div className="min-h-[400px]">
                {activeTab === 'overview' && (
                    <OverviewTab study={study} dimensionData={dimensionData} />
                )}

                {activeTab === 'sites' && (
                    <SitesTab
                        table={table}
                        globalFilter={globalFilter}
                        setGlobalFilter={setGlobalFilter}
                        study={study}
                    />
                )}

                {activeTab === 'dqi' && (
                    <DQITab dimensionData={dimensionData} trendData={trendData} />
                )}

                {activeTab === 'agents' && (
                    <AgentsTab studyId={study.study_id} />
                )}
            </div>
        </div>
    );
}


// Overview Tab Component
function OverviewTab({ study, dimensionData }: { study: Study; dimensionData: any[] }) {
    return (
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
            {/* KPI Cards */}
            <div className="lg:col-span-2 grid grid-cols-2 gap-4">
                <div className="bg-white dark:bg-slate-800 p-6 rounded-xl shadow-sm border border-slate-200 dark:border-slate-700">
                    <h3 className="text-sm font-medium text-slate-500 dark:text-slate-400 uppercase tracking-wide">Enrollment</h3>
                    <div className="mt-2 flex items-baseline gap-2">
                        <span className="text-3xl font-bold text-slate-900 dark:text-white">{study.enrollment_percentage || 0}%</span>
                        <span className="text-sm text-green-600 font-medium">On Track</span>
                    </div>
                    <div className="mt-4 w-full bg-slate-100 dark:bg-slate-700 rounded-full h-2">
                        <div
                            className="bg-blue-600 h-2 rounded-full transition-all duration-500"
                            style={{ width: `${study.enrollment_percentage || 0}%` }}
                        />
                    </div>
                </div>
                <div className="bg-white dark:bg-slate-800 p-6 rounded-xl shadow-sm border border-slate-200 dark:border-slate-700">
                    <h3 className="text-sm font-medium text-slate-500 dark:text-slate-400 uppercase tracking-wide">Sites Active</h3>
                    <div className="mt-2 text-3xl font-bold text-slate-900 dark:text-white">{study.sites?.length || 0}</div>
                    <div className="mt-1 text-sm text-slate-400">Across multiple regions</div>
                </div>
                <div className="bg-white dark:bg-slate-800 p-6 rounded-xl shadow-sm border border-slate-200 dark:border-slate-700">
                    <h3 className="text-sm font-medium text-slate-500 dark:text-slate-400 uppercase tracking-wide">Pending Actions</h3>
                    <div className="mt-2 text-3xl font-bold text-amber-600">
                        {study.sites?.reduce((sum, s) => sum + s.queries, 0) || 0}
                    </div>
                    <div className="mt-1 text-sm text-slate-400">Open queries</div>
                </div>
                <div className="bg-white dark:bg-slate-800 p-6 rounded-xl shadow-sm border border-slate-200 dark:border-slate-700">
                    <h3 className="text-sm font-medium text-slate-500 dark:text-slate-400 uppercase tracking-wide">Est. Completion</h3>
                    <div className="mt-2 text-2xl font-bold text-slate-900 dark:text-white">
                        {study.timeline?.est_completion
                            ? new Date(study.timeline.est_completion).toLocaleDateString()
                            : 'TBD'}
                    </div>
                </div>
            </div>

            {/* Right column: Pipeline Status + AI Insights */}
            <div className="space-y-4">
                {/* Pipeline Status Card */}
                <PipelineStatusCard compact />

                {/* AI Insights */}
                <div className="bg-gradient-to-br from-indigo-900 to-purple-900 text-white p-6 rounded-xl shadow-sm">
                    <div className="flex items-center gap-2 mb-4">
                        <span className="text-xl">✨</span>
                        <h3 className="font-bold">AI Recommendations</h3>
                    </div>
                    <ul className="space-y-4 text-sm text-indigo-100">
                        {dimensionData
                            .filter(d => d.score < 70)
                            .slice(0, 2)
                            .map((d, i) => (
                                <li key={i} className="bg-white/10 p-3 rounded-lg">
                                    <strong>{d.dimension}:</strong> Score of {Math.round(d.score)} is below target.
                                    Consider reviewing related metrics.
                                </li>
                            ))}
                        {dimensionData.filter(d => d.score < 70).length === 0 && (
                            <li className="bg-white/10 p-3 rounded-lg">
                                <strong>All Clear:</strong> All dimension scores are within acceptable ranges.
                            </li>
                        )}
                    </ul>
                </div>
            </div>
        </div>
    );
}

// Sites Tab Component with TanStack Table
function SitesTab({ table, globalFilter, setGlobalFilter, study }: {
    table: any;
    globalFilter: string;
    setGlobalFilter: (value: string) => void;
    study: Study;
}) {
    return (
        <div className="space-y-4">
            {/* Filters */}
            <div className="flex items-center justify-between">
                <div className="flex items-center gap-4">
                    <input
                        type="text"
                        value={globalFilter}
                        onChange={(e) => setGlobalFilter(e.target.value)}
                        placeholder="Search sites..."
                        className="px-4 py-2 border border-slate-300 dark:border-slate-600 rounded-lg bg-white dark:bg-slate-800 text-slate-900 dark:text-white placeholder-slate-400 focus:ring-2 focus:ring-indigo-500 focus:border-transparent"
                    />
                    <select
                        onChange={(e) => {
                            const value = e.target.value;
                            table.getColumn('risk_level')?.setFilterValue(value ? [value] : undefined);
                        }}
                        className="px-4 py-2 border border-slate-300 dark:border-slate-600 rounded-lg bg-white dark:bg-slate-800 text-slate-900 dark:text-white"
                    >
                        <option value="">All Risk Levels</option>
                        <option value="Critical">Critical</option>
                        <option value="High">High</option>
                        <option value="Medium">Medium</option>
                        <option value="Low">Low</option>
                    </select>
                </div>
                <div className="text-sm text-slate-500 dark:text-slate-400">
                    Showing {table.getFilteredRowModel().rows.length} of {study.sites?.length || 0} sites
                </div>
            </div>

            {/* Table */}
            <div className="bg-white dark:bg-slate-800 shadow-sm rounded-xl border border-slate-200 dark:border-slate-700 overflow-hidden">
                <table className="min-w-full divide-y divide-slate-200 dark:divide-slate-700">
                    <thead className="bg-slate-50 dark:bg-slate-900">
                        {table.getHeaderGroups().map((headerGroup: any) => (
                            <tr key={headerGroup.id}>
                                {headerGroup.headers.map((header: any) => (
                                    <th
                                        key={header.id}
                                        onClick={header.column.getToggleSortingHandler()}
                                        className={cn(
                                            'px-6 py-3 text-left text-xs font-bold text-slate-500 dark:text-slate-400 uppercase tracking-wider',
                                            header.column.getCanSort() && 'cursor-pointer hover:bg-slate-100 dark:hover:bg-slate-800'
                                        )}
                                    >
                                        <div className="flex items-center gap-2">
                                            {flexRender(header.column.columnDef.header, header.getContext())}
                                            {header.column.getIsSorted() && (
                                                <span>{header.column.getIsSorted() === 'asc' ? '↑' : '↓'}</span>
                                            )}
                                        </div>
                                    </th>
                                ))}
                            </tr>
                        ))}
                    </thead>
                    <tbody className="bg-white dark:bg-slate-800 divide-y divide-slate-200 dark:divide-slate-700">
                        {table.getRowModel().rows.length > 0 ? (
                            table.getRowModel().rows.map((row: any) => (
                                <tr key={row.id} className="hover:bg-slate-50 dark:hover:bg-slate-700/50 transition-colors">
                                    {row.getVisibleCells().map((cell: any) => (
                                        <td key={cell.id} className="px-6 py-4 whitespace-nowrap text-sm text-slate-900 dark:text-slate-100">
                                            {flexRender(cell.column.columnDef.cell, cell.getContext())}
                                        </td>
                                    ))}
                                </tr>
                            ))
                        ) : (
                            <tr>
                                <td colSpan={6} className="px-6 py-12 text-center text-slate-500 dark:text-slate-400">
                                    <div className="text-4xl mb-2">📋</div>
                                    No sites match your filters
                                </td>
                            </tr>
                        )}
                    </tbody>
                </table>
            </div>
        </div>
    );
}


// DQI Analysis Tab Component
function DQITab({ dimensionData, trendData }: {
    dimensionData: any[];
    trendData: any[];
}) {
    return (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            {/* Dimension Breakdown */}
            <div className="bg-white dark:bg-slate-800 p-6 rounded-xl shadow-sm border border-slate-200 dark:border-slate-700">
                <h3 className="text-lg font-semibold text-slate-900 dark:text-white mb-4">DQI Dimension Breakdown</h3>
                <div className="h-72">
                    <ResponsiveContainer width="100%" height="100%">
                        <RadarChart data={dimensionData}>
                            <PolarGrid stroke="#e2e8f0" />
                            <PolarAngleAxis dataKey="dimension" tick={{ fill: '#64748b', fontSize: 12 }} />
                            <PolarRadiusAxis angle={30} domain={[0, 100]} tick={{ fill: '#64748b' }} />
                            <Radar
                                name="Score"
                                dataKey="score"
                                stroke="#6366f1"
                                fill="#6366f1"
                                fillOpacity={0.3}
                                strokeWidth={2}
                            />
                        </RadarChart>
                    </ResponsiveContainer>
                </div>
            </div>

            {/* DQI Trend */}
            <div className="bg-white dark:bg-slate-800 p-6 rounded-xl shadow-sm border border-slate-200 dark:border-slate-700">
                <h3 className="text-lg font-semibold text-slate-900 dark:text-white mb-4">DQI Trend (6 Weeks)</h3>
                <div className="h-72">
                    <ResponsiveContainer width="100%" height="100%">
                        <LineChart data={trendData}>
                            <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
                            <XAxis dataKey="week" stroke="#64748b" />
                            <YAxis domain={[0, 100]} stroke="#64748b" />
                            <Tooltip
                                contentStyle={{
                                    backgroundColor: '#1e293b',
                                    border: 'none',
                                    borderRadius: '8px',
                                    color: '#f1f5f9',
                                }}
                            />
                            <Line
                                type="monotone"
                                dataKey="dqi"
                                stroke="#6366f1"
                                strokeWidth={3}
                                dot={{ fill: '#6366f1', strokeWidth: 2 }}
                                activeDot={{ r: 6 }}
                            />
                        </LineChart>
                    </ResponsiveContainer>
                </div>
            </div>

            {/* Dimension Details */}
            <div className="lg:col-span-2 bg-white dark:bg-slate-800 p-6 rounded-xl shadow-sm border border-slate-200 dark:border-slate-700">
                <h3 className="text-lg font-semibold text-slate-900 dark:text-white mb-4">Dimension Details</h3>
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-5 gap-4">
                    {dimensionData.map((dim) => (
                        <div key={dim.dimension} className="p-4 bg-slate-50 dark:bg-slate-700/50 rounded-lg">
                            <div className="flex items-center justify-between mb-2">
                                <span className="text-sm font-medium text-slate-700 dark:text-slate-300">{dim.dimension}</span>
                                <span className="text-xs text-slate-500 dark:text-slate-400">{dim.weight}%</span>
                            </div>
                            <div className="text-2xl font-bold text-slate-900 dark:text-white">{Math.round(dim.score)}</div>
                            <div className="mt-2 w-full bg-slate-200 dark:bg-slate-600 rounded-full h-2">
                                <div
                                    className={cn(
                                        'h-2 rounded-full transition-all duration-500',
                                        dim.score >= 85 ? 'bg-green-500' :
                                            dim.score >= 65 ? 'bg-amber-500' :
                                                dim.score >= 40 ? 'bg-orange-500' : 'bg-red-500'
                                    )}
                                    style={{ width: `${dim.score}%` }}
                                />
                            </div>
                        </div>
                    ))}
                </div>
            </div>
        </div>
    );
}

// Agent Signals Tab Component - Uses real AgentOrchestrationPanel
function AgentsTab({ studyId }: { studyId: string }) {
    return (
        <div className="space-y-6">
            {/* Header */}
            <div className="bg-indigo-50 dark:bg-indigo-900/20 border border-indigo-200 dark:border-indigo-800 rounded-xl p-4">
                <div className="flex items-center gap-3">
                    <span className="text-2xl">🤖</span>
                    <div>
                        <h3 className="font-semibold text-indigo-900 dark:text-indigo-100">Multi-Agent Analysis for {studyId}</h3>
                        <p className="text-sm text-indigo-700 dark:text-indigo-300">
                            7 specialized AI agents analyze this study's data quality in real-time
                        </p>
                    </div>
                </div>
            </div>

            {/* Agent Orchestration Panel - Real component with live data */}
            <AgentOrchestrationPanel studyId={studyId} />
        </div>
    );
}
