/**
 * useSystemStatus Hook
 * =====================
 * Fetches real-time system metrics and Guardian status.
 * 
 * Features:
 * - Live system health from /api/v1/metrics
 * - Guardian status from /api/v1/guardian/status
 * - Polling with configurable interval
 * - Loading and error states
 */

import { useQuery } from '@tanstack/react-query';

// Types matching backend response
export interface SystemHealth {
    status: 'healthy' | 'degraded' | 'critical';
    healthyAgents: number;
    totalAgents: number;
    activeStudies: number;
    staleEntities: number;
    criticalEvents: number;
    warningEvents: number;
    uptimeHours: number;
    dataFreshnessScore: number;
}

export interface AgentMetric {
    agent_name: string;
    status: string;
    avg_confidence: number;
}

export interface MetricsResponse {
    system: {
        status: string;
        healthy_agents: number;
        total_agents: number;
        active_studies: number;
        stale_entities: number;
        data_freshness_score: number;
    };
    agents: AgentMetric[];
}

export interface GuardianStatusResponse {
    status: 'healthy' | 'warning' | 'error';
    last_check: string;
    data_output_consistency: string;
    staleness_detected: boolean;
    integrity_warnings: number;
    events: GuardianEvent[];
}

export interface GuardianEvent {
    event_id: string;
    event_type: string;
    severity: string;
    message: string;
    timestamp: string;
    remediation_suggestion?: string;
}

// API Base URL
const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000';

// Fetch helper
async function fetchAPI<T>(endpoint: string): Promise<T> {
    const response = await fetch(`${API_BASE}${endpoint}`, {
        headers: { 'Content-Type': 'application/json' },
    });

    if (!response.ok) {
        throw new Error(`API error: ${response.status}`);
    }

    return response.json();
}

/**
 * useSystemStatus - Fetch system health and metrics
 */
export function useSystemStatus(options?: {
    pollingInterval?: number;
    enabled?: boolean;
}) {
    const { pollingInterval = 30000, enabled = true } = options || {};

    const metricsQuery = useQuery({
        queryKey: ['metrics'],
        queryFn: () => fetchAPI<MetricsResponse>('/api/v1/metrics'),
        enabled,
        refetchInterval: pollingInterval > 0 ? pollingInterval : undefined,
        staleTime: 30000,
    });

    const guardianQuery = useQuery({
        queryKey: ['guardian-status'],
        queryFn: () => fetchAPI<GuardianStatusResponse>('/api/v1/guardian/status'),
        enabled,
        refetchInterval: pollingInterval > 0 ? pollingInterval : undefined,
        staleTime: 30000,
    });

    // Transform API response to SystemHealth format
    const systemHealth: SystemHealth | null = metricsQuery.data ? {
        status: metricsQuery.data.system.status as 'healthy' | 'degraded' | 'critical',
        healthyAgents: metricsQuery.data.system.healthy_agents,
        totalAgents: metricsQuery.data.system.total_agents,
        activeStudies: metricsQuery.data.system.active_studies,
        staleEntities: metricsQuery.data.system.stale_entities,
        criticalEvents: guardianQuery.data?.events?.filter(e => e.severity === 'critical').length ?? 0,
        warningEvents: guardianQuery.data?.events?.filter(e => e.severity === 'warning').length ?? 0,
        uptimeHours: 24, 
        dataFreshnessScore: metricsQuery.data.system.data_freshness_score,
    } : null;

    return {
        systemHealth,
        guardianStatus: guardianQuery.data ?? null,
        agentMetrics: metricsQuery.data?.agents ?? [],
        isLoading: metricsQuery.isLoading || guardianQuery.isLoading,
        isFetching: metricsQuery.isFetching || guardianQuery.isFetching,
        isError: metricsQuery.isError || guardianQuery.isError,
        error: metricsQuery.error || guardianQuery.error,
        refetch: () => {
            metricsQuery.refetch();
            guardianQuery.refetch();
        },
    };
}

/**
 * useGuardianEvents - Fetch Guardian events with optional limit
 */
export function useGuardianEvents(options?: {
    limit?: number;
    pollingInterval?: number;
}) {
    const { limit = 50, pollingInterval = 30000 } = options || {};

    return useQuery({
        queryKey: ['guardian-events', limit],
        queryFn: () => fetchAPI<GuardianEvent[]>(`/api/v1/guardian/events?limit=${limit}`),
        refetchInterval: pollingInterval > 0 ? pollingInterval : undefined,
        staleTime: 15000,
    });
}

export default useSystemStatus;
