/**
 * useAnalysis Hook
 * =================
 * Real-time analysis data fetching with cache-first pattern.
 * 
 * Features:
 * - Polling for live updates (configurable interval)
 * - Loading states during recompute
 * - Cache hit/miss indicators
 * - Last updated timestamps
 * - Auto-refresh when data changes
 */

import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';

// Types
export interface AgentSignal {
    agent_name: string;
    agent_type: string;
    risk_level: string | null;
    confidence: number | null;
    processing_time_ms: number;
    abstained: boolean;
    error: string | null;
}

export interface ConsensusDecision {
    risk_level: string;
    confidence: number;
    risk_score: number;
    recommended_action: string;
    explanation: string;
}

export interface DQIScore {
    overall_score: number;
    risk_level: string;
    threshold_met: string;
    dimension_scores: Record<string, number>;
}

export interface AnalysisResult {
    study_id: string;
    timestamp: string;
    cached: boolean;
    cache_age_seconds: number | null;
    agent_signals: AgentSignal[];
    consensus: ConsensusDecision | null;
    dqi_score: DQIScore | null;
    processing_time_ms: number;
    agents_succeeded: number;
    agents_failed: number;
    agents_abstained: number;
}

export interface SystemStatus {
    status: string;
    pipeline: {
        total_executions: number;
        total_time_ms: number;
        avg_time_ms: number;
        agent_count: number;
        guardian_enabled: boolean;
    };
    cache: {
        total_requests: number;
        cache_hits: number;
        cache_misses: number;
        hit_rate: string;
        entries_count: number;
    };
    timestamp: string;
}

// API Base URL
const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000';

// Fetch helper with error handling
async function fetchAPI<T>(endpoint: string, options?: RequestInit): Promise<T> {
    const response = await fetch(`${API_BASE}${endpoint}`, {
        ...options,
        headers: {
            'Content-Type': 'application/json',
            ...options?.headers,
        },
    });

    if (!response.ok) {
        const error = await response.json().catch(() => ({ detail: 'Unknown error' }));
        throw new Error(error.detail || `API error: ${response.status}`);
    }

    return response.json();
}

// ========================================
// HOOKS
// ========================================

/**
 * useAnalysis - Fetch analysis for a study with real-time updates
 */
export function useAnalysis(studyId: string, options?: {
    enabled?: boolean;
    pollingInterval?: number;  // ms, 0 to disable
    refetchOnWindowFocus?: boolean;
}) {
    const {
        enabled = true,
        pollingInterval = 30000,  // 30s default
        refetchOnWindowFocus = true,
    } = options || {};

    const queryClient = useQueryClient();
    const [isRefreshing, setIsRefreshing] = useState(false);

    const query = useQuery({
        queryKey: ['analysis', studyId],
        queryFn: () => fetchAPI<AnalysisResult>(`/api/v1/analysis/${studyId}`),
        enabled: enabled && !!studyId,
        refetchInterval: pollingInterval > 0 ? pollingInterval : undefined,
        refetchOnWindowFocus,
        staleTime: 60000,  // Consider data fresh for 1 minute
    });

    // Force refresh mutation
    const refreshMutation = useMutation({
        mutationFn: () => fetchAPI<AnalysisResult>(`/api/v1/analysis/${studyId}?force_refresh=true`, {
            method: 'POST',
        }),
        onMutate: () => setIsRefreshing(true),
        onSettled: () => setIsRefreshing(false),
        onSuccess: (data) => {
            queryClient.setQueryData(['analysis', studyId], data);
        },
    });

    // Derived state
    const cacheInfo = {
        isCached: query.data?.cached ?? false,
        cacheAge: query.data?.cache_age_seconds ?? null,
        lastUpdated: query.data?.timestamp ? new Date(query.data.timestamp) : null,
    };

    return {
        data: query.data,
        isLoading: query.isLoading,
        isFetching: query.isFetching,
        isRefreshing,
        isError: query.isError,
        error: query.error,
        cacheInfo,
        refresh: () => refreshMutation.mutate(),
        refetch: () => query.refetch(),
    };
}

/**
 * useSystemStatus - Fetch system status with cache and pipeline metrics
 */
export function useSystemStatus(options?: {
    pollingInterval?: number;
}) {
    const { pollingInterval = 60000 } = options || {};  // 1 minute

    return useQuery({
        queryKey: ['system-status'],
        queryFn: () => fetchAPI<SystemStatus>('/api/v1/analysis/status/system'),
        refetchInterval: pollingInterval > 0 ? pollingInterval : undefined,
    });
}

/**
 * useRefreshAll - Trigger refresh for all studies
 */
export function useRefreshAll() {
    const queryClient = useQueryClient();

    return useMutation({
        mutationFn: () => fetchAPI<{ status: string; message: string; studies_queued: number }>(
            '/api/v1/analysis/refresh',
            { method: 'POST' }
        ),
        onSuccess: () => {
            // Invalidate all analysis queries to trigger refetch
            queryClient.invalidateQueries({ queryKey: ['analysis'] });
        },
    });
}

/**
 * useStudyList - Fetch list of studies
 */
export function useStudyList() {
    return useQuery({
        queryKey: ['studies'],
        queryFn: () => fetchAPI<Array<{
            study_id: string;
            study_name: string;
            enrollment_percentage: number | null;
            dqi_score: number | null;
            risk_level: string | null;
            file_types_available: string[];
        }>>('/api/v1/studies'),
        staleTime: 5 * 60 * 1000,  // 5 minutes
    });
}

/**
 * useMetrics - Fetch system metrics
 */
export function useMetrics() {
    return useQuery({
        queryKey: ['metrics'],
        queryFn: () => fetchAPI<{
            system: {
                status: string;
                healthy_agents: number;
                total_agents: number;
                active_studies: number;
                stale_entities: number;
                data_freshness_score: number;
            };
            agents: Array<{
                agent_name: string;
                status: string;
                avg_confidence: number;
            }>;
        }>('/api/v1/metrics'),
        refetchInterval: 30000,  // 30s
    });
}

export default useAnalysis;
