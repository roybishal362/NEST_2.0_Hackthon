/**
 * AI Insights Page - Detailed Agent Analysis
 * ==========================================
 * Displays detailed agent insights from the 7-agent pipeline
 * Connected to /api/v1/studies/{study_id}/agents endpoint
 */
import { useEffect, useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';

// TypeScript interfaces matching API response
interface AgentEvidence {
  feature: string;
  value: any;
  threshold?: number;
  severity: number;
}

interface AgentInsight {
  name: string;
  type: string;
  risk_level: string;
  confidence: number;
  weight: number;
  abstained: boolean;
  evidence: AgentEvidence[];
  recommended_actions: string[];
}

interface Consensus {
  risk_level: string;
  confidence: number;
  agent_votes?: Record<string, number>;
  weighted_score?: number;
  reasoning?: string;
}

interface AgentInsightsResponse {
  study_id: string;
  agents: AgentInsight[];
  consensus: Consensus;
  timestamp: string;
}

// Helper function to get risk level color
function getRiskColor(risk: string): string {
  switch (risk.toLowerCase()) {
    case 'critical':
      return 'text-red-400 bg-red-900/30 border-red-800';
    case 'high':
      return 'text-orange-400 bg-orange-900/30 border-orange-800';
    case 'medium':
      return 'text-yellow-400 bg-yellow-900/30 border-yellow-800';
    case 'low':
      return 'text-green-400 bg-green-900/30 border-green-800';
    default:
      return 'text-gray-400 bg-gray-800 border-gray-700';
  }
}

// Helper function to get severity color
function getSeverityColor(severity: number): string {
  if (severity >= 0.8) return 'bg-red-900/30 text-red-400';
  if (severity >= 0.5) return 'bg-orange-900/30 text-orange-400';
  if (severity >= 0.3) return 'bg-yellow-900/30 text-yellow-400';
  return 'bg-green-900/30 text-green-400';
}

// Agent Consensus Card Component
function AgentConsensusCard({ agents, consensus }: { agents: AgentInsight[]; consensus: Consensus }) {
  return (
    <div className="bg-slate-800 rounded-lg shadow p-6 mb-6 border border-slate-700">
      <h2 className="text-xl font-bold mb-4 text-white">Agent Consensus</h2>

      <div className="mb-4">
        <div className="text-3xl font-bold text-white">
          Final Risk:{' '}
          <span className={getRiskColor(consensus.risk_level)}>
            {consensus.risk_level.toUpperCase()}
          </span>
        </div>
        <div className="text-slate-400 mt-2">
          Confidence: {(consensus.confidence * 100).toFixed(0)}%
        </div>
        {consensus.reasoning && (
          <div className="text-sm text-slate-400 mt-2 italic">
            {consensus.reasoning}
          </div>
        )}
      </div>

      <div className="space-y-2">
        <h3 className="font-semibold text-white">Agent Votes:</h3>
        {agents.map((agent) => (
          <div
            key={agent.name}
            className="flex items-center justify-between p-2 bg-slate-700 rounded"
          >
            <div className="flex items-center gap-2">
              <span className="font-medium text-white">{agent.name}</span>
              <span className="text-sm text-slate-400">({agent.weight}x)</span>
            </div>
            <div className="flex items-center gap-2">
              {agent.abstained ? (
                <span className="text-slate-400">ABSTAINED</span>
              ) : (
                <>
                  <span className={getRiskColor(agent.risk_level)}>
                    {agent.risk_level.toUpperCase()}
                  </span>
                  <span className="text-sm text-slate-400">
                    {(agent.confidence * 100).toFixed(0)}%
                  </span>
                </>
              )}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

// Feature Evidence Table Component
function FeatureEvidenceTable({ agent }: { agent: AgentInsight }) {
  if (agent.abstained || agent.evidence.length === 0) {
    return null;
  }

  return (
    <div className="mt-4">
      <h4 className="font-semibold mb-2 text-white">Evidence:</h4>
      <table className="w-full text-sm">
        <thead>
          <tr className="border-b border-slate-700">
            <th className="text-left p-2 text-slate-300">Feature</th>
            <th className="text-right p-2 text-slate-300">Value</th>
            <th className="text-right p-2 text-slate-300">Threshold</th>
            <th className="text-center p-2 text-slate-300">Severity</th>
          </tr>
        </thead>
        <tbody>
          {agent.evidence.map((e, idx) => (
            <tr key={idx} className="border-b border-slate-700">
              <td className="p-2 text-slate-300">{e.feature}</td>
              <td className="text-right p-2 text-slate-300">
                {typeof e.value === 'number' ? e.value.toFixed(2) : String(e.value)}
              </td>
              <td className="text-right p-2 text-slate-300">
                {e.threshold !== undefined ? e.threshold.toFixed(2) : '-'}
              </td>
              <td className="text-center p-2">
                <span className={`px-2 py-1 rounded ${getSeverityColor(e.severity)}`}>
                  {(e.severity * 100).toFixed(0)}%
                </span>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

// Agent Detail Card Component
function AgentDetailCard({ agent }: { agent: AgentInsight }) {
  return (
    <div className="bg-slate-800 rounded-lg shadow p-6 mb-4 border border-slate-700">
      <div className="flex items-center justify-between mb-4">
        <div>
          <h3 className="text-lg font-bold text-white">{agent.name}</h3>
          <p className="text-sm text-slate-400">{agent.type}</p>
        </div>
        <div className="text-right">
          {agent.abstained ? (
            <span className="px-3 py-1 rounded-full bg-slate-700 text-slate-400 text-sm">
              ABSTAINED
            </span>
          ) : (
            <>
              <div className={`px-3 py-1 rounded-full text-sm font-medium ${getRiskColor(agent.risk_level)}`}>
                {agent.risk_level.toUpperCase()}
              </div>
              <div className="text-sm text-slate-400 mt-1">
                Confidence: {(agent.confidence * 100).toFixed(0)}%
              </div>
            </>
          )}
        </div>
      </div>

      {/* Evidence Table */}
      <FeatureEvidenceTable agent={agent} />

      {/* Recommended Actions */}
      {agent.recommended_actions && agent.recommended_actions.length > 0 && (
        <div className="mt-4">
          <h4 className="font-semibold mb-2 text-white">Recommended Actions:</h4>
          <ul className="list-disc list-inside space-y-1">
            {agent.recommended_actions.map((action, idx) => (
              <li key={idx} className="text-sm text-slate-300">
                {action}
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}

// Main Page Component
export default function AIInsightsNew() {
  const { studyId } = useParams<{ studyId: string }>();
  const navigate = useNavigate();
  const [insights, setInsights] = useState<AgentInsightsResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!studyId) {
      setError('No study ID provided');
      setLoading(false);
      return;
    }

    // Fetch agent insights from API
    fetch(`http://localhost:8000/api/v1/studies/${studyId}/agents`)
      .then((res) => {
        if (!res.ok) {
          throw new Error(`HTTP ${res.status}: ${res.statusText}`);
        }
        return res.json();
      })
      .then((data) => {
        setInsights(data);
        setLoading(false);
      })
      .catch((err) => {
        console.error('Failed to fetch agent insights:', err);
        setError(err.message);
        setLoading(false);
      });
  }, [studyId]);

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-slate-400">Loading agent insights...</div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="bg-red-900/30 border border-red-800 rounded-lg p-6">
        <h2 className="text-red-400 font-bold mb-2">Error Loading Insights</h2>
        <p className="text-red-300">{error}</p>
        <button
          onClick={() => navigate(-1)}
          className="mt-4 px-4 py-2 bg-red-600 text-white rounded hover:bg-red-700"
        >
          Go Back
        </button>
      </div>
    );
  }

  if (!insights) {
    return (
      <div className="text-slate-400">No insights available</div>
    );
  }

  return (
    <div className="p-6">
      {/* Header */}
      <div className="mb-6">
        <button
          onClick={() => navigate(-1)}
          className="text-indigo-400 hover:text-indigo-300 mb-2"
        >
          ← Back
        </button>
        <h1 className="text-2xl font-bold mb-2 text-white">
          AI Insights for {insights.study_id}
        </h1>
        <p className="text-slate-400 text-sm">
          Analysis performed at {new Date(insights.timestamp).toLocaleString()}
        </p>
      </div>

      {/* Agent Consensus Card */}
      <AgentConsensusCard agents={insights.agents} consensus={insights.consensus} />

      {/* Individual Agent Cards */}
      <div>
        <h2 className="text-xl font-bold mb-4 text-white">Individual Agent Analysis</h2>
        {insights.agents.map((agent) => (
          <AgentDetailCard key={agent.name} agent={agent} />
        ))}
      </div>
    </div>
  );
}
