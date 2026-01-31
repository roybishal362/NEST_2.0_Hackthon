/**
 * Guardian Dashboard Page
 * =======================
 * Displays Guardian Agent system health, integrity alerts, and agent performance.
 * 
 * Features:
 * - System health status
 * - Recent integrity alerts
 * - Agent performance metrics
 * - Real-time monitoring
 */

import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';

// TYPE DEFINITIONS

interface SystemHealth {
  status: string;
  agents_operational: number;
  last_check: string;
  event_storage_health: string;
  staleness_tracking_health: string;
}

interface IntegrityAlert {
  event_id: string;
  event_type: string;
  severity: string;
  entity_id: string;
  snapshot_id: string;
  data_delta_summary: string;
  expected_behavior: string;
  actual_behavior: string;
  recommendation: string;
  timestamp: string;
}

interface AgentPerformance {
  agent_name: string;
  signals_generated: number;
  abstention_rate: number;
  avg_confidence: number;
  last_run: string | null;
}

interface GuardianStatus {
  system_health: SystemHealth;
  integrity_alerts: IntegrityAlert[];
  agent_performance: AgentPerformance[];
  diagnostic_report: any;
}

// ========================================
// MAIN COMPONENT
// ========================================

export default function GuardianDashboard() {
  const [status, setStatus] = useState<GuardianStatus | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetchGuardianStatus();
    
    // Auto-refresh every 30 seconds
    const interval = setInterval(fetchGuardianStatus, 30000);
    return () => clearInterval(interval);
  }, []);

  const fetchGuardianStatus = async () => {
    try {
      const response = await fetch('http://localhost:8000/api/v1/guardian/status');
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }
      const data = await response.json();
      setStatus(data);
      setError(null);
    } catch (err) {
      console.error('Error fetching Guardian status:', err);
      setError(err instanceof Error ? err.message : 'Failed to fetch Guardian status');
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-slate-50 dark:bg-slate-900 p-6">
        <div className="max-w-7xl mx-auto">
          <div className="animate-pulse">
            <div className="h-8 bg-slate-200 dark:bg-slate-700 rounded w-1/3 mb-6"></div>
            <div className="grid grid-cols-4 gap-4 mb-6">
              {[1, 2, 3, 4].map(i => (
                <div key={i} className="h-24 bg-slate-200 dark:bg-slate-700 rounded-xl"></div>
              ))}
            </div>
          </div>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="min-h-screen bg-slate-50 dark:bg-slate-900 p-6">
        <div className="max-w-7xl mx-auto">
          <div className="bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg p-6">
            <h2 className="text-xl font-bold text-red-800 dark:text-red-200 mb-2">Error Loading Guardian Status</h2>
            <p className="text-red-600 dark:text-red-300">{error}</p>
            <button
              onClick={fetchGuardianStatus}
              className="mt-4 px-4 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700 transition-colors"
            >
              Retry
            </button>
          </div>
        </div>
      </div>
    );
  }

  if (!status) {
    return null;
  }

  const getStatusColor = (statusValue: string) => {
    switch (statusValue.toUpperCase()) {
      case 'HEALTHY':
        return 'bg-green-500';
      case 'DEGRADED':
        return 'bg-yellow-500';
      case 'CRITICAL':
        return 'bg-red-500';
      default:
        return 'bg-slate-500';
    }
  };

  const getSeverityColor = (severity: string) => {
    switch (severity.toLowerCase()) {
      case 'critical':
        return 'bg-red-100 text-red-800 dark:bg-red-900/30 dark:text-red-200';
      case 'high':
        return 'bg-orange-100 text-orange-800 dark:bg-orange-900/30 dark:text-orange-200';
      case 'medium':
        return 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900/30 dark:text-yellow-200';
      case 'low':
        return 'bg-blue-100 text-blue-800 dark:bg-blue-900/30 dark:text-blue-200';
      default:
        return 'bg-slate-100 text-slate-800 dark:bg-slate-800 dark:text-slate-200';
    }
  };

  return (
    <div className="min-h-screen bg-slate-50 dark:bg-slate-900 p-6">
      <div className="max-w-7xl mx-auto space-y-6">
        {/* Header */}
        <header className="flex items-center justify-between">
          <div>
            <h1 className="text-3xl font-bold text-slate-900 dark:text-white">
              🛡️ Guardian System Monitor
            </h1>
            <p className="text-slate-600 dark:text-slate-400 mt-1">
              Real-time system integrity monitoring
            </p>
          </div>
          <div className="flex items-center gap-3">
            <button
              onClick={fetchGuardianStatus}
              className="px-4 py-2 bg-white dark:bg-slate-800 text-slate-700 dark:text-slate-200 rounded-lg hover:bg-slate-100 dark:hover:bg-slate-700 transition-colors shadow-sm border border-slate-200 dark:border-slate-700"
            >
              🔄 Refresh
            </button>
            <div className={`${getStatusColor(status.system_health.status)} text-white px-4 py-2 rounded-full text-xs font-bold uppercase tracking-wider shadow-sm`}>
              {status.system_health.status}
            </div>
          </div>
        </header>

        {/* System Health Metrics */}
        <section className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
          <SystemHealthCard
            title="Agents Operational"
            value={`${status.system_health.agents_operational}/7`}
            icon="🤖"
            color="blue"
          />
          <SystemHealthCard
            title="Event Storage"
            value={status.system_health.event_storage_health}
            icon="💾"
            color="indigo"
          />
          <SystemHealthCard
            title="Staleness Tracking"
            value={status.system_health.staleness_tracking_health}
            icon="⏰"
            color="purple"
          />
          <SystemHealthCard
            title="Integrity Alerts"
            value={status.integrity_alerts.length.toString()}
            icon="🚨"
            color="amber"
          />
        </section>

        {/* Agent Performance */}
        <section className="bg-white dark:bg-slate-800 rounded-xl shadow-sm border border-slate-200 dark:border-slate-700 p-6">
          <h2 className="text-xl font-bold text-slate-900 dark:text-white mb-4">
            Agent Performance
          </h2>
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead>
                <tr className="border-b border-slate-200 dark:border-slate-700">
                  <th className="text-left py-3 px-4 text-sm font-semibold text-slate-700 dark:text-slate-300">Agent</th>
                  <th className="text-right py-3 px-4 text-sm font-semibold text-slate-700 dark:text-slate-300">Signals</th>
                  <th className="text-right py-3 px-4 text-sm font-semibold text-slate-700 dark:text-slate-300">Abstention Rate</th>
                  <th className="text-right py-3 px-4 text-sm font-semibold text-slate-700 dark:text-slate-300">Avg Confidence</th>
                  <th className="text-right py-3 px-4 text-sm font-semibold text-slate-700 dark:text-slate-300">Last Run</th>
                </tr>
              </thead>
              <tbody>
                {status.agent_performance.map((agent, idx) => (
                  <tr key={idx} className="border-b border-slate-100 dark:border-slate-700/50 hover:bg-slate-50 dark:hover:bg-slate-700/30 transition-colors">
                    <td className="py-3 px-4 font-medium text-slate-900 dark:text-white">{agent.agent_name}</td>
                    <td className="py-3 px-4 text-right text-slate-600 dark:text-slate-400">{agent.signals_generated}</td>
                    <td className="py-3 px-4 text-right text-slate-600 dark:text-slate-400">{(agent.abstention_rate * 100).toFixed(1)}%</td>
                    <td className="py-3 px-4 text-right">
                      <span className="inline-flex items-center px-2 py-1 rounded-full text-xs font-medium bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-200">
                        {(agent.avg_confidence * 100).toFixed(0)}%
                      </span>
                    </td>
                    <td className="py-3 px-4 text-right text-sm text-slate-500 dark:text-slate-400">
                      {agent.last_run ? new Date(agent.last_run).toLocaleTimeString() : 'Never'}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>

        {/* Integrity Alerts */}
        <section className="bg-white dark:bg-slate-800 rounded-xl shadow-sm border border-slate-200 dark:border-slate-700 p-6">
          <h2 className="text-xl font-bold text-slate-900 dark:text-white mb-4">
            Recent Integrity Alerts
          </h2>
          {status.integrity_alerts.length === 0 ? (
            <div className="text-center py-8 text-slate-500 dark:text-slate-400">
              <div className="text-4xl mb-2">✅</div>
              <p>No integrity alerts detected</p>
              <p className="text-sm mt-1">System is operating normally</p>
            </div>
          ) : (
            <div className="space-y-3">
              {status.integrity_alerts.map((alert, idx) => (
                <div
                  key={idx}
                  className="border border-slate-200 dark:border-slate-700 rounded-lg p-4 hover:shadow-md transition-shadow"
                >
                  <div className="flex items-start justify-between mb-2">
                    <div className="flex items-center gap-2">
                      <span className={`px-2 py-1 rounded-full text-xs font-bold uppercase ${getSeverityColor(alert.severity)}`}>
                        {alert.severity}
                      </span>
                      <span className="text-sm font-medium text-slate-700 dark:text-slate-300">
                        {alert.event_type}
                      </span>
                    </div>
                    <span className="text-xs text-slate-500 dark:text-slate-400">
                      {new Date(alert.timestamp).toLocaleString()}
                    </span>
                  </div>
                  <div className="space-y-2 text-sm">
                    <div>
                      <span className="font-semibold text-slate-700 dark:text-slate-300">Entity:</span>{' '}
                      <span className="text-slate-600 dark:text-slate-400">{alert.entity_id}</span>
                    </div>
                    <div>
                      <span className="font-semibold text-slate-700 dark:text-slate-300">Issue:</span>{' '}
                      <span className="text-slate-600 dark:text-slate-400">{alert.data_delta_summary}</span>
                    </div>
                    <div className="bg-slate-50 dark:bg-slate-900/50 rounded p-3 mt-2">
                      <div className="font-semibold text-slate-700 dark:text-slate-300 mb-1">Recommendation:</div>
                      <div className="text-slate-600 dark:text-slate-400">{alert.recommendation}</div>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </section>

        {/* Back to Portfolio */}
        <div className="flex justify-center">
          <Link
            to="/portfolio"
            className="inline-flex items-center gap-2 px-6 py-3 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors shadow-sm"
          >
            ← Back to Portfolio
          </Link>
        </div>
      </div>
    </div>
  );
}

// ========================================
// HELPER COMPONENTS
// ========================================

interface SystemHealthCardProps {
  title: string;
  value: string;
  icon: string;
  color: 'blue' | 'indigo' | 'purple' | 'amber';
}

function SystemHealthCard({ title, value, icon, color }: SystemHealthCardProps) {
  const colorClasses = {
    blue: 'from-blue-500 to-blue-600',
    indigo: 'from-indigo-500 to-indigo-600',
    purple: 'from-purple-500 to-purple-600',
    amber: 'from-amber-500 to-amber-600',
  };

  return (
    <div className={`bg-gradient-to-br ${colorClasses[color]} p-6 rounded-xl text-white shadow-lg hover:shadow-xl transition-shadow`}>
      <div className="flex items-center gap-4">
        <div className="text-4xl">{icon}</div>
        <div>
          <div className="text-3xl font-bold">{value}</div>
          <div className="text-sm opacity-90 uppercase tracking-wide">{title}</div>
        </div>
      </div>
    </div>
  );
}
