// Site Detail Page - Subject-Level Drill-Down
// ========================================
import { useParams, useNavigate, useSearchParams } from 'react-router-dom';
import { useState } from 'react';
import { cn } from '@/lib/utils';

// Mock subject data
const generateSubjects = (siteId: string) => {
    const count = Math.floor(Math.random() * 15) + 5;
    return Array.from({ length: count }, (_, i) => ({
        subject_id: `${siteId}-SUBJ-${String(i + 1).padStart(3, '0')}`,
        status: ['Active', 'Completed', 'Withdrawn', 'Screening'][Math.floor(Math.random() * 4)],
        visits_completed: Math.floor(Math.random() * 12) + 1,
        visits_total: 12,
        queries_open: Math.floor(Math.random() * 5),
        last_visit: new Date(Date.now() - Math.random() * 30 * 24 * 60 * 60 * 1000).toLocaleDateString(),
        data_completeness: Math.floor(Math.random() * 30) + 70,
    }));
};

export default function SiteDetail() {
    const { studyId, siteId } = useParams<{ studyId: string; siteId: string }>();
    const navigate = useNavigate();
    const [searchParams] = useSearchParams();
    const fromStudy = searchParams.get('from');

    const [subjects] = useState(() => generateSubjects(siteId || 'SITE-001'));
    const [filter, setFilter] = useState('');
    const [statusFilter, setStatusFilter] = useState('');

    const filteredSubjects = subjects.filter(s => {
        const matchesSearch = s.subject_id.toLowerCase().includes(filter.toLowerCase());
        const matchesStatus = !statusFilter || s.status === statusFilter;
        return matchesSearch && matchesStatus;
    });

    // Calculate site metrics
    const totalQueries = subjects.reduce((sum, s) => sum + s.queries_open, 0);
    const avgCompleteness = Math.round(subjects.reduce((sum, s) => sum + s.data_completeness, 0) / subjects.length);
    const activeSubjects = subjects.filter(s => s.status === 'Active').length;

    const getStatusColor = (status: string) => {
        switch (status) {
            case 'Active': return 'bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-400';
            case 'Completed': return 'bg-blue-100 text-blue-800 dark:bg-blue-900/30 dark:text-blue-400';
            case 'Withdrawn': return 'bg-red-100 text-red-800 dark:bg-red-900/30 dark:text-red-400';
            case 'Screening': return 'bg-amber-100 text-amber-800 dark:bg-amber-900/30 dark:text-amber-400';
            default: return 'bg-slate-100 text-slate-800 dark:bg-slate-700 dark:text-slate-300';
        }
    };

    return (
        <div className="space-y-8">
            {/* Breadcrumb */}
            <nav className="flex items-center gap-2 text-sm text-slate-500 dark:text-slate-400">
                <button onClick={() => navigate('/portfolio')} className="hover:text-indigo-600">Portfolio</button>
                <span>→</span>
                <button 
                    onClick={() => navigate(`/studies/${studyId}${fromStudy ? `?tab=sites` : ''}`)} 
                    className="hover:text-indigo-600"
                >
                    {studyId}
                </button>
                <span>→</span>
                <span className="text-slate-900 dark:text-white font-medium">{siteId}</span>
            </nav>

            {/* Header */}
            <div className="bg-white dark:bg-slate-800 p-6 rounded-xl shadow-sm border border-slate-200 dark:border-slate-700">
                <div className="flex items-start justify-between">
                    <div>
                        <h1 className="text-3xl font-bold text-slate-900 dark:text-white">{siteId}</h1>
                        <p className="text-slate-500 dark:text-slate-400 mt-1">Site detail for study {studyId}</p>
                    </div>
                    <button
                        onClick={() => navigate(`/studies/${studyId}?tab=sites`)}
                        className="px-4 py-2 text-sm font-medium text-indigo-600 hover:text-indigo-800 dark:text-indigo-400"
                    >
                        ← Back to Sites
                    </button>
                </div>

                {/* Site Metrics */}
                <div className="grid grid-cols-4 gap-4 mt-6">
                    <div className="p-4 bg-slate-50 dark:bg-slate-700/50 rounded-lg">
                        <div className="text-sm text-slate-500 dark:text-slate-400">Total Subjects</div>
                        <div className="text-2xl font-bold text-slate-900 dark:text-white">{subjects.length}</div>
                    </div>
                    <div className="p-4 bg-slate-50 dark:bg-slate-700/50 rounded-lg">
                        <div className="text-sm text-slate-500 dark:text-slate-400">Active Subjects</div>
                        <div className="text-2xl font-bold text-green-600">{activeSubjects}</div>
                    </div>
                    <div className="p-4 bg-slate-50 dark:bg-slate-700/50 rounded-lg">
                        <div className="text-sm text-slate-500 dark:text-slate-400">Open Queries</div>
                        <div className="text-2xl font-bold text-amber-600">{totalQueries}</div>
                    </div>
                    <div className="p-4 bg-slate-50 dark:bg-slate-700/50 rounded-lg">
                        <div className="text-sm text-slate-500 dark:text-slate-400">Avg Completeness</div>
                        <div className="text-2xl font-bold text-slate-900 dark:text-white">{avgCompleteness}%</div>
                    </div>
                </div>
            </div>

            {/* Filters */}
            <div className="flex items-center gap-4">
                <input
                    type="text"
                    value={filter}
                    onChange={(e) => setFilter(e.target.value)}
                    placeholder="Search subjects..."
                    className="px-4 py-2 border border-slate-300 dark:border-slate-600 rounded-lg bg-white dark:bg-slate-800 text-slate-900 dark:text-white placeholder-slate-400 focus:ring-2 focus:ring-indigo-500"
                />
                <select
                    value={statusFilter}
                    onChange={(e) => setStatusFilter(e.target.value)}
                    className="px-4 py-2 border border-slate-300 dark:border-slate-600 rounded-lg bg-white dark:bg-slate-800 text-slate-900 dark:text-white"
                >
                    <option value="">All Statuses</option>
                    <option value="Active">Active</option>
                    <option value="Completed">Completed</option>
                    <option value="Withdrawn">Withdrawn</option>
                    <option value="Screening">Screening</option>
                </select>
                <span className="text-sm text-slate-500 dark:text-slate-400 ml-auto">
                    Showing {filteredSubjects.length} of {subjects.length} subjects
                </span>
            </div>

            {/* Subject Table */}
            <div className="bg-white dark:bg-slate-800 shadow-sm rounded-xl border border-slate-200 dark:border-slate-700 overflow-hidden">
                <table className="min-w-full divide-y divide-slate-200 dark:divide-slate-700">
                    <thead className="bg-slate-50 dark:bg-slate-900">
                        <tr>
                            <th className="px-6 py-3 text-left text-xs font-bold text-slate-500 dark:text-slate-400 uppercase">Subject ID</th>
                            <th className="px-6 py-3 text-left text-xs font-bold text-slate-500 dark:text-slate-400 uppercase">Status</th>
                            <th className="px-6 py-3 text-center text-xs font-bold text-slate-500 dark:text-slate-400 uppercase">Visits</th>
                            <th className="px-6 py-3 text-center text-xs font-bold text-slate-500 dark:text-slate-400 uppercase">Open Queries</th>
                            <th className="px-6 py-3 text-left text-xs font-bold text-slate-500 dark:text-slate-400 uppercase">Last Visit</th>
                            <th className="px-6 py-3 text-left text-xs font-bold text-slate-500 dark:text-slate-400 uppercase">Data Completeness</th>
                        </tr>
                    </thead>
                    <tbody className="divide-y divide-slate-200 dark:divide-slate-700">
                        {filteredSubjects.map((subject) => (
                            <tr key={subject.subject_id} className="hover:bg-slate-50 dark:hover:bg-slate-700/50">
                                <td className="px-6 py-4 text-sm font-medium text-slate-900 dark:text-white">
                                    {subject.subject_id}
                                </td>
                                <td className="px-6 py-4">
                                    <span className={cn('px-2 py-1 text-xs font-medium rounded-full', getStatusColor(subject.status))}>
                                        {subject.status}
                                    </span>
                                </td>
                                <td className="px-6 py-4 text-center text-sm text-slate-700 dark:text-slate-300">
                                    {subject.visits_completed} / {subject.visits_total}
                                </td>
                                <td className="px-6 py-4 text-center">
                                    <span className={cn(
                                        'text-sm font-medium',
                                        subject.queries_open > 0 ? 'text-amber-600' : 'text-slate-500'
                                    )}>
                                        {subject.queries_open}
                                    </span>
                                </td>
                                <td className="px-6 py-4 text-sm text-slate-500 dark:text-slate-400">
                                    {subject.last_visit}
                                </td>
                                <td className="px-6 py-4">
                                    <div className="flex items-center gap-2">
                                        <div className="w-24 bg-slate-200 dark:bg-slate-700 rounded-full h-2">
                                            <div
                                                className={cn(
                                                    'h-2 rounded-full',
                                                    subject.data_completeness >= 90 ? 'bg-green-500' :
                                                    subject.data_completeness >= 70 ? 'bg-amber-500' : 'bg-red-500'
                                                )}
                                                style={{ width: `${subject.data_completeness}%` }}
                                            />
                                        </div>
                                        <span className="text-sm text-slate-700 dark:text-slate-300">{subject.data_completeness}%</span>
                                    </div>
                                </td>
                            </tr>
                        ))}
                    </tbody>
                </table>
            </div>
        </div>
    );
}
