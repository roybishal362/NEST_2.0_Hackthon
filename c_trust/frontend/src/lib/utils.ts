// Utility Functions
// ========================================

import { clsx, type ClassValue } from 'clsx';
import { twMerge } from 'tailwind-merge';
import type { RiskLevel } from '@/types/api';

/**
 * Merge class names with Tailwind CSS
 */
export function cn(...inputs: ClassValue[]) {
    return twMerge(clsx(inputs));
}

/**
 * Get color class for risk level
 */
export function getRiskColor(riskLevel: RiskLevel | null): string {
    switch (riskLevel) {
        case 'Critical':
            return 'bg-red-500';
        case 'High':
            return 'bg-orange-500';
        case 'Medium':
            return 'bg-yellow-400';
        case 'Low':
            return 'bg-green-500';
        default:
            return 'bg-gray-400';
    }
}

/**
 * Get label for risk level
 */
export function getRiskLabel(riskLevel: RiskLevel | null): string {
    switch (riskLevel) {
        case 'Critical':
            return 'CRITICAL';
        case 'High':
            return 'High Risk';
        case 'Medium':
            return 'At Risk';
        case 'Low':
            return 'On Track';
        default:
            return 'Unknown';
    }
}

/**
 * Format percentage
 */
export function formatPercentage(value: number | null): string {
    if (value === null || value === undefined) return 'N/A';
    return `${Math.round(value)}%`;
}

/**
 * Format DQI score
 */
export function formatDQI(score: number | null): string {
    if (score === null || score === undefined) return '--';
    return Math.round(score).toString();
}

/**
 * Get DQI band color
 */
export function getDQIBandColor(score: number | null): string {
    if (score === null || score === undefined) return 'bg-gray-400';
    if (score >= 85) return 'bg-green-500';
    if (score >= 65) return 'bg-amber-500';
    if (score >= 40) return 'bg-orange-500';
    return 'bg-red-500';
}

/**
 * Get DQI band label
 */
export function getDQIBandLabel(score: number | null): string {
    if (score === null || score === undefined) return 'Unknown';
    if (score >= 85) return 'Green';
    if (score >= 65) return 'Amber';
    if (score >= 40) return 'Orange';
    return 'Red';
}
