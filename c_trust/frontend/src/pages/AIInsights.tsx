/**
 * AI Insights Page - Agent Signals and Recommendations
 * ====================================================
 * Connected to LIVE API data via React Query hooks.
 * Falls back to demo data when API is unavailable.
 */
import { useNavigate } from 'react-router-dom';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { agentsAPI, guardianAPI, notificationsAPI } from '@/services/api';
import type { AgentStatus, GuardianStatus, Notification } from '@/types/api';
import { cn } from '@/lib/utils';

// Priority badge styling
function getPriorityBadge(priority: string) {
    switch (priority) {
        case 'critical': return 'bg-red-100 text-red-800 border-red-200 dark:bg-red-900/30 dark:text-red-400 dark:border-red-800';
        case 'high': return 'bg-orange-100 text-orange-800 border-orange-200 dark:bg-orange-900/30 dark:text-orange-400 dark:border-orange-800';
        case 'medium': return 'bg-amber-100 text-amber-800 border-amber-200 dark:bg-amber-900/30 dark:text-amber-400 dark:border-amber-800';
        default: return 'bg-slate-100 text-slate-800 border-slate-200 dark:bg-slate-700 dark:text-slate-300 dark:border-slate-600';
    }
}

// Fallback mock data
const mockAgents: AgentStatus[] = [
    { agent_id: 'completeness', agent_name: 'Data Completeness Agent', status: 'active', confidence: 0.92, last_run: '2 hours ago', signals_count: 2 },
    { agent_id: 'safety', agent_name: 'Safety & Compliance Agent', status: 'active', confidence: 0.88, last_run: '2 hours ago', signals_count: 2 },
    { agent_id: 'query', agent_name: 'Query Quality Agent', status: 'active', confidence: 0.95, last_run: '2 hours ago', signals_count: 1 },
    { agent_id: 'coding', agent_name: 'Coding Readiness Agent', status: 'active', confidence: 0.91, last_run: '2 hours ago', signals_count: 0 },
    { agent_id: 'stability', agent_name: 'Stability Agent', status: 'active', confidence: 0.87, last_run: '3 hours ago', signals_count: 1 },
    { agent_id: 'temporal', agent_name: 'Temporal Drift Agent', status: 'active', confidence: 0.89, last_run: '2 hours ago', signals_count: 1 },
    { agent_id: 'cross-evidence', agent_name: 'Cross-Evidence Agent', status: 'active', confidence: 0.93, last_run: '1 hour ago', signals_count: 0 },
];

const mockGuardianStatus: GuardianStatus = {
    status: 'healthy',
    last_check: '30 minutes ago',
    data_output_consistency: 'verified',
    staleness_detected: false,
    integrity_warnings: 0,
    events: [],
};

const mockNotifications: Notification[] = [
    { id: '1', type: 'recommendation', priority: 'critical', title: 'Immediate SAE Review Required', message: 'Study 08 has 3 SAEs that have been pending review for more than 48 hours.', action: 'Review and resolve SAEs immediately', study_id: 'STUDY_08', acknowledged: false, created_at: new Date().toISOString() },
    { id: '2', type: 'alert', priority: 'high', title: 'Data Entry Lag Detected', message: 'Site SITE-101 in Study 05 shows a 5-day lag in data entry.', action: 'Contact site coordinator for status update', study_id: 'STUDY_05', acknowledged: false, created_at: new Date().toISOString() },
    { id: '3', type: 'recommendation', priority: 'medium', title: 'Query Resolution Velocity Declining', message: 'Query resolution time has increased by 40% over the past 2 weeks.', action: 'Review query management process', study_id: 'STUDY_02', acknowledged: true, created_at: new Date().toISOString() },
];

export default function AIInsights() {
    const navigate = useNavigate();
    const queryClient = useQueryClient();

    // React Query hooks for data fetching with auto-refresh
    const agentsQuery = useQuery({
        queryKey: ['agents'],
        queryFn: () => agentsAPI.getAll(),
        staleTime: 30000,
        refetchInterval: 30000, // Poll every 30s
        retry: 1,
    });

    const guardianQuery = useQuery({
        queryKey: ['guardian-status'],
        queryFn: () => guardianAPI.getStatus(),
        staleTime: 30000,
        refetchInterval: 60000, // Poll every 60s
        retry: 1,
    });

    const notificationsQuery = useQuery({
        queryKey: ['notifications'],
        queryFn: () => notificationsAPI.getAll(),
        staleTime: 15000,
        refetchInterval: 15000, // Poll every 15s for notifications
        retry: 1,
    });

    // Acknowledge mutation
    const acknowledgeMutation = useMutation({
        mutationFn: (id: string) => notificationsAPI.acknowledge(id),
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ['notifications'] });
        },
    });

    // Determine if using live or fallback data
    const isLiveData = agentsQuery.isSuccess || guardianQuery.isSuccess || notificationsQuery.isSuccess;
    const agents = agentsQuery.data ?? mockAgents;
    const guardianStatus = guardianQuery.data ?? mockGuardianStatus;
    const notifications = notificationsQuery.data ?? mockNotifications;

    const isLoading = agentsQuery.isLoading && guardianQuery.isLoading && notificationsQuery.isLoading;
    const isFetching = agentsQuery.isFetching || guardianQuery.isFetching || notificationsQuery.isFetching;

    const handleAcknowledge = async (id: string) => {
        try {
            await acknowledgeMutation.mutateAsync(id);
        } catch {
            // Fallback: update local state for demo mode
            queryClient.setQueryData<Notification[]>(['notifications'], (old) =>
                (old ?? notifications).map(n => n.id === id ? { ...n, acknowledged: true } : n)
            );
        }
    };

    const handleRefresh = () => {
        agentsQuery.refetch();
        guardianQuery.refetch();
        notificationsQuery.refetch();
    };

    if (isLoading) {
        return (
            <div className="space-y-8 animate-pulse">
                <div className="h-8 bg-slate-200 dark:bg-slate-700 rounded w-1/4"></div>
                <div className="h-48 bg-slate-200 dark:bg-slate-700 rounded-xl"></div>
                <div className="grid grid-cols-3 gap-4">
                    {[1, 2, 3].map(i => (
                        <div key={i} className="h-48 bg-slate-200 dark:bg-slate-700 rounded-xl"></div>
                    ))}
                </div>
            </div>
        );
    }

    return (
        <div className="space-y-8">
            <header className="flex items-center justify-between">
                <div>
                    <h1 className="text-3xl font-bold text-slate-900 dark:text-white tracking-tight">AI Insights</h1>
                    <p className="text-slate-500 dark:text-slate-400 mt-2">
                        Multi-agent intelligence signals and recommendations.
                        {isFetching && <span className="text-indigo-500 ml-2">Updating...</span>}
                    </p>
                </div>
                <div className="flex items-center gap-3">
                    <button
                        onClick={handleRefresh}
                        className="px-4 py-2 bg-slate-100 dark:bg-slate-700 text-slate-700 dark:text-slate-200 rounded-lg hover:bg-slate-200 dark:hover:bg-slate-600 transition-colors"
                    >
                        🔄 Refresh
                    </button>
                    {isLiveData ? (
                        <span className="px-3 py-1 bg-green-100 dark:bg-green-900/30 text-green-800 dark:text-green-400 text-sm rounded-full flex items-center gap-2">
                            <span className="w-2 h-2 bg-green-500 rounded-full animate-pulse"></span>
                            Live Data
                        </span>
                    ) : (
                        <span className="px-3 py-1 bg-amber-100 dark:bg-amber-900/30 text-amber-800 dark:text-amber-400 text-sm rounded-full">
                            Demo Data
                        </span>
                    )}
                </div>
            </header>

            {/* Guardian Agent Status */}
            <div className="bg-gradient-to-r from-indigo-600 to-purple-600 p-6 rounded-xl text-white">
                <div className="flex items-center justify-between">
                    <div className="flex items-center gap-4">
                        <div className="w-12 h-12 bg-white/20 rounded-xl flex items-center justify-center">
                            <span className="text-2xl">🛡️</span>
                        </div>
                        <div>
                            <h2 className="text-xl font-bold">Guardian System Integrity Agent</h2>
                            <p className="text-indigo-200 text-sm">Monitoring system behavior consistency</p>
                        </div>
                    </div>
                    <div className="text-right">
                        <div className={cn(
                            'inline-flex items-center gap-2 px-3 py-1 rounded-full text-sm font-medium',
                            guardianStatus.status === 'healthy'
                                ? 'bg-green-500/20 text-green-100'
                                : guardianStatus.status === 'warning'
                                    ? 'bg-amber-500/20 text-amber-100'
                                    : 'bg-red-500/20 text-red-100'
                        )}>
                            <span className={cn(
                                'w-2 h-2 rounded-full',
                                guardianStatus.status === 'healthy' ? 'bg-green-400' :
                                    guardianStatus.status === 'warning' ? 'bg-amber-400' : 'bg-red-400'
                            )}></span>
                            {guardianStatus.status === 'healthy' ? 'System Healthy' :
                                guardianStatus.status === 'warning' ? 'Warnings Detected' : 'Issues Detected'}
                        </div>
                        <div className="text-indigo-200 text-xs mt-1">Last check: {guardianStatus.last_check}</div>
                    </div>
                </div>
                <div className="grid grid-cols-3 gap-4 mt-6">
                    <div className="bg-white/10 rounded-lg p-4">
                        <div className="text-indigo-200 text-sm">Data-Output Consistency</div>
                        <div className="text-lg font-semibold mt-1 capitalize">{guardianStatus.data_output_consistency}</div>
                    </div>
                    <div className="bg-white/10 rounded-lg p-4">
                        <div className="text-indigo-200 text-sm">Staleness Detection</div>
                        <div className="text-lg font-semibold mt-1">{guardianStatus.staleness_detected ? 'Detected' : 'None'}</div>
                    </div>
                    <div className="bg-white/10 rounded-lg p-4">
                        <div className="text-indigo-200 text-sm">Integrity Warnings</div>
                        <div className="text-lg font-semibold mt-1">{guardianStatus.integrity_warnings}</div>
                    </div>
                </div>
            </div>

            {/* Agent Status Cards - All 7 Agents */}
            <div>
                <h2 className="text-xl font-bold text-slate-900 dark:text-white mb-4">
                    Signal Agents
                    <span className="ml-2 text-sm font-normal text-slate-500">({agents.length} agents)</span>
                </h2>
                <div className="grid grid-cols-1 md:grid-cols-3 lg:grid-cols-4 gap-4">
                    {agents.map(agent => (
                        <div key={agent.agent_id} className="bg-white dark:bg-slate-800 p-5 rounded-xl shadow-sm border border-slate-200 dark:border-slate-700">
                            <div className="flex items-center justify-between mb-4">
                                <h3 className="font-semibold text-slate-900 dark:text-white text-sm">{agent.agent_name}</h3>
                                <span className={cn(
                                    'w-2 h-2 rounded-full',
                                    agent.status === 'active' ? 'bg-green-500' :
                                        agent.status === 'error' ? 'bg-red-500' : 'bg-slate-400'
                                )}></span>
                            </div>
                            <div className="space-y-2 text-sm">
                                <div className="flex justify-between">
                                    <span className="text-slate-500 dark:text-slate-400">Confidence</span>
                                    <span className="font-medium text-slate-900 dark:text-white">{(agent.confidence * 100).toFixed(0)}%</span>
                                </div>
                                <div className="flex justify-between">
                                    <span className="text-slate-500 dark:text-slate-400">Last Run</span>
                                    <span className="text-slate-700 dark:text-slate-300">{agent.last_run}</span>
                                </div>
                                <div className="flex justify-between">
                                    <span className="text-slate-500 dark:text-slate-400">Active Signals</span>
                                    <span className="font-medium text-slate-900 dark:text-white">{agent.signals_count}</span>
                                </div>
                            </div>
                            <div className="mt-4 pt-4 border-t border-slate-100 dark:border-slate-700">
                                <div className="w-full bg-slate-200 dark:bg-slate-700 rounded-full h-2">
                                    <div
                                        className={cn(
                                            "h-2 rounded-full transition-all duration-500",
                                            agent.confidence >= 0.9 ? "bg-green-500" :
                                                agent.confidence >= 0.7 ? "bg-indigo-600" :
                                                    "bg-amber-500"
                                        )}
                                        style={{ width: `${agent.confidence * 100}%` }}
                                    />
                                </div>
                            </div>
                        </div>
                    ))}
                </div>
            </div>

            {/* Recommendations */}
            <div>
                <div className="flex items-center justify-between mb-4">
                    <h2 className="text-xl font-bold text-slate-900 dark:text-white">AI Recommendations</h2>
                    <span className="text-sm text-slate-500 dark:text-slate-400">
                        {notifications.filter(n => !n.acknowledged).length} pending
                    </span>
                </div>
                <div className="space-y-4">
                    {notifications.map(notification => (
                        <div
                            key={notification.id}
                            className={cn(
                                'bg-white dark:bg-slate-800 p-5 rounded-xl shadow-sm border border-slate-200 dark:border-slate-700 transition-opacity',
                                notification.acknowledged && 'opacity-60'
                            )}
                        >
                            <div className="flex items-start justify-between">
                                <div className="flex-1">
                                    <div className="flex items-center gap-3 mb-2">
                                        <span className={cn('px-2 py-0.5 text-xs font-semibold rounded border', getPriorityBadge(notification.priority || 'medium'))}>
                                            {(notification.priority || 'medium').toUpperCase()}
                                        </span>
                                        {notification.study_id && (
                                            <button
                                                onClick={() => navigate(`/studies/${notification.study_id}`)}
                                                className="text-xs text-indigo-600 dark:text-indigo-400 hover:underline"
                                            >
                                                {notification.study_id}
                                            </button>
                                        )}
                                    </div>
                                    <h3 className="font-semibold text-slate-900 dark:text-white">{notification.title}</h3>
                                    <p className="text-sm text-slate-600 dark:text-slate-400 mt-1">{notification.message}</p>
                                    {notification.action && (
                                        <div className="mt-3 flex items-center gap-2">
                                            <span className="text-xs font-medium text-slate-500 dark:text-slate-400">Recommended Action:</span>
                                            <span className="text-xs text-indigo-600 dark:text-indigo-400">{notification.action}</span>
                                        </div>
                                    )}
                                </div>
                                <div className="ml-4">
                                    {notification.acknowledged ? (
                                        <span className="text-xs text-green-600 dark:text-green-400 font-medium">✓ Acknowledged</span>
                                    ) : (
                                        <button
                                            onClick={() => handleAcknowledge(notification.id)}
                                            disabled={acknowledgeMutation.isPending}
                                            className="px-4 py-2 bg-indigo-600 text-white text-sm font-medium rounded-lg hover:bg-indigo-700 transition-colors disabled:opacity-50"
                                        >
                                            {acknowledgeMutation.isPending ? 'Saving...' : 'Acknowledge'}
                                        </button>
                                    )}
                                </div>
                            </div>
                        </div>
                    ))}
                </div>
            </div>
        </div>
    );
}
