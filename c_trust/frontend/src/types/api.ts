// C-TRUST API Client - Type Definitions
// ========================================

export type RiskLevel = 'Critical' | 'High' | 'Medium' | 'Low' | 'Unknown';

export interface SiteSummary {
    site_id: string;
    enrollment: number;
    saes: number;
    queries: number;
    risk_level: RiskLevel;
}

export interface StudyTimeline {
    phase: string;
    status: string;
    enrollment_pct: number;
    est_completion?: string;
}

export interface Study {
    study_id: string;
    study_name: string;
    enrollment_percentage: number | null;
    dqi_score: number | null;
    risk_level: RiskLevel | null;
    file_types_available: string[];
    // Detailed fields
    sites?: SiteSummary[];
    timeline?: StudyTimeline;
    dimension_scores?: Record<string, any>;
    last_refresh?: string;
}

export interface DashboardSummary {
    total_studies: number;
    avg_dqi: number;
    critical_risks: number;
    sites_at_risk: number;
    total_patients: number;
}

export interface DQIScore {
    study_id: string;
    overall_score: number;
    risk_level: RiskLevel;
    threshold_met: string;
    dimension_scores: DimensionScore[];
    timestamp: string;
}

export interface DimensionScore {
    dimension: string;
    raw_score: number;
    weight: number;
    weighted_score: number;
    contributing_features: Record<string, number>;
}

export interface APIError {
    error: string;
    detail?: string;
    timestamp: string;
}

// Agent Types
export interface AgentSignal {
    agent_id: string;
    agent_name: string;
    signal_type: string;
    severity: 'critical' | 'high' | 'medium' | 'low';
    confidence: number;
    message: string;
    study_id?: string;
    site_id?: string;
    timestamp: string;
    evidence?: Record<string, any>;
}

export interface AgentStatus {
    agent_id: string;
    agent_name: string;
    status: 'active' | 'inactive' | 'error';
    confidence: number;
    last_run: string;
    signals_count: number;
}

export interface GuardianStatus {
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
}

export interface Notification {
    id: string;
    type: 'alert' | 'recommendation' | 'info';
    priority: 'critical' | 'high' | 'medium' | 'low';
    title: string;
    message: string;
    study_id?: string;
    site_id?: string;
    acknowledged: boolean;
    created_at: string;
    action?: string;
}

export interface Recommendation {
    id: string;
    priority: 'critical' | 'high' | 'medium' | 'low';
    title: string;
    description: string;
    action: string;
    study_id?: string;
    acknowledged: boolean;
    evidence?: string[];
}
