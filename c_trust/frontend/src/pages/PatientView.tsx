/**
 * Patient View Page
 * =================
 * Displays patient-level details including demographics, visit timeline, SAEs, and queries.
 * Part of multi-level drill-down: Portfolio → Study → Site → Patient
 */

import { useEffect, useState } from 'react';
import { useParams, useNavigate, useSearchParams, Link } from 'react-router-dom';
import { cn } from '@/lib/utils';

// ========================================
// TYPE DEFINITIONS
// ========================================

interface PatientDetail {
  patient_id: string;
  enrollment_date: string;
  status: string;
  visits_completed: number;
  visits_total: number;
  saes: number;
  queries: number;
  last_visit: string;
}

interface Visit {
  visit_id: string;
  visit_name: string;
  scheduled_date: string;
  actual_date?: string;
  status: 'completed' | 'scheduled' | 'missed' | 'overdue';
  forms_completed: number;
  forms_total: number;
}

interface SAE {
  sae_id: string;
  event_term: string;
  onset_date: string;
  severity: 'mild' | 'moderate' | 'severe';
  outcome: string;
  reported_date: string;
  days_to_report: number;
}

interface Query {
  query_id: string;
  form: string;
  field: string;
  query_text: string;
  opened_date: string;
  status: 'open' | 'answered' | 'closed';
  priority: 'low' | 'medium' | 'high';
}

// ========================================
// MAIN COMPONENT
// ========================================

export default function PatientView() {
  const { studyId, siteId, patientId } = useParams<{ 
    studyId: string; 
    siteId: string; 
    patientId: string;
  }>();
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();

  const [patient, setPatient] = useState<PatientDetail | null>(null);
  const [visits, setVisits] = useState<Visit[]>([]);
  const [saes, setSaes] = useState<SAE[]>([]);
  const [queries, setQueries] = useState<Query[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (patientId && siteId) {
      fetchPatientData();
    }
  }, [patientId, siteId]);

  const fetchPatientData = async () => {
    try {
      setLoading(true);
      
      // Fetch patient details from site patients endpoint
      const patientsResponse = await fetch(
        `http://localhost:8000/api/v1/sites/${siteId}/patients`
      );
      if (!patientsResponse.ok) {
        throw new Error(`Failed to fetch patients: ${patientsResponse.status}`);
      }
      const patientsData = await patientsResponse.json();
      
      // Find this specific patient
      const patientData = patientsData.find((p: PatientDetail) => p.patient_id === patientId);
      if (!patientData) {
        throw new Error('Patient not found');
      }
      setPatient(patientData);

      // Generate mock visit data (in production, this would come from API)
      const mockVisits = generateMockVisits(patientData);
      setVisits(mockVisits);

      // Generate mock SAE data if patient has SAEs
      if (patientData.saes > 0) {
        const mockSaes = generateMockSAEs(patientData);
        setSaes(mockSaes);
      }

      // Generate mock query data if patient has queries
      if (patientData.queries > 0) {
        const mockQueries = generateMockQueries(patientData);
        setQueries(mockQueries);
      }

      setError(null);
    } catch (err) {
      console.error('Error fetching patient data:', err);
      setError(err instanceof Error ? err.message : 'Failed to load patient data');
    } finally {
      setLoading(false);
    }
  };

  // Mock data generators (in production, these would be API calls)
  const generateMockVisits = (patient: PatientDetail): Visit[] => {
    const visits: Visit[] = [];
    const visitNames = ['Screening', 'Baseline', 'Week 4', 'Week 8', 'Week 12', 'Week 16'];
    
    for (let i = 0; i < patient.visits_total; i++) {
      const isCompleted = i < patient.visits_completed;
      const scheduledDate = new Date(patient.enrollment_date);
      scheduledDate.setDate(scheduledDate.getDate() + (i * 28)); // Every 4 weeks
      
      visits.push({
        visit_id: `V${i + 1}`,
        visit_name: visitNames[i] || `Visit ${i + 1}`,
        scheduled_date: scheduledDate.toISOString(),
        actual_date: isCompleted ? scheduledDate.toISOString() : undefined,
        status: isCompleted ? 'completed' : (i === patient.visits_completed ? 'scheduled' : 'scheduled'),
        forms_completed: isCompleted ? 8 : 0,
        forms_total: 8
      });
    }
    
    return visits;
  };

  const generateMockSAEs = (patient: PatientDetail): SAE[] => {
    const saes: SAE[] = [];
    const events = ['Chest Pain', 'Severe Headache', 'Allergic Reaction', 'Hospitalization'];
    
    for (let i = 0; i < patient.saes; i++) {
      const onsetDate = new Date(patient.enrollment_date);
      onsetDate.setDate(onsetDate.getDate() + (i * 45 + 30));
      
      const reportedDate = new Date(onsetDate);
      reportedDate.setDate(reportedDate.getDate() + 2);
      
      saes.push({
        sae_id: `SAE_${i + 1}`,
        event_term: events[i % events.length],
        onset_date: onsetDate.toISOString(),
        severity: i % 3 === 0 ? 'severe' : (i % 2 === 0 ? 'moderate' : 'mild'),
        outcome: 'Resolved',
        reported_date: reportedDate.toISOString(),
        days_to_report: 2
      });
    }
    
    return saes;
  };

  const generateMockQueries = (patient: PatientDetail): Query[] => {
    const queries: Query[] = [];
    const forms = ['Demographics', 'Vital Signs', 'Lab Results', 'Adverse Events'];
    const fields = ['Date', 'Value', 'Units', 'Comments'];
    
    for (let i = 0; i < patient.queries; i++) {
      const openedDate = new Date(patient.enrollment_date);
      openedDate.setDate(openedDate.getDate() + (i * 20 + 10));
      
      queries.push({
        query_id: `Q_${i + 1}`,
        form: forms[i % forms.length],
        field: fields[i % fields.length],
        query_text: 'Please clarify the entered value',
        opened_date: openedDate.toISOString(),
        status: i % 3 === 0 ? 'open' : (i % 2 === 0 ? 'answered' : 'closed'),
        priority: i % 4 === 0 ? 'high' : (i % 2 === 0 ? 'medium' : 'low')
      });
    }
    
    return queries;
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-slate-50 dark:bg-slate-900 p-6">
        <div className="max-w-7xl mx-auto">
          <div className="animate-pulse space-y-6">
            <div className="h-32 bg-slate-200 dark:bg-slate-700 rounded-xl"></div>
            <div className="grid grid-cols-3 gap-4">
              {[1, 2, 3].map(i => (
                <div key={i} className="h-24 bg-slate-200 dark:bg-slate-700 rounded-xl"></div>
              ))}
            </div>
            <div className="h-96 bg-slate-200 dark:bg-slate-700 rounded-xl"></div>
          </div>
        </div>
      </div>
    );
  }

  if (error || !patient) {
    return (
      <div className="min-h-screen bg-slate-50 dark:bg-slate-900 p-6">
        <div className="max-w-7xl mx-auto">
          <div className="bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg p-6">
            <h2 className="text-xl font-bold text-red-800 dark:text-red-200 mb-2">
              Error Loading Patient
            </h2>
            <p className="text-red-600 dark:text-red-300">{error || 'Patient not found'}</p>
            <button
              onClick={() => navigate(`/studies/${studyId}/sites/${siteId}`)}
              className="mt-4 px-4 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700 transition-colors"
            >
              Back to Site
            </button>
          </div>
        </div>
      </div>
    );
  }

  const getStatusColor = (status: string) => {
    switch (status.toLowerCase()) {
      case 'active':
        return 'text-green-600 bg-green-100 dark:bg-green-900/30 dark:text-green-200';
      case 'completed':
        return 'text-blue-600 bg-blue-100 dark:bg-blue-900/30 dark:text-blue-200';
      case 'withdrawn':
        return 'text-red-600 bg-red-100 dark:bg-red-900/30 dark:text-red-200';
      default:
        return 'text-slate-600 bg-slate-100 dark:bg-slate-800 dark:text-slate-200';
    }
  };

  const getVisitStatusColor = (status: string) => {
    switch (status) {
      case 'completed':
        return 'bg-green-500';
      case 'scheduled':
        return 'bg-blue-500';
      case 'missed':
        return 'bg-red-500';
      case 'overdue':
        return 'bg-orange-500';
      default:
        return 'bg-slate-500';
    }
  };

  const getSeverityColor = (severity: string) => {
    switch (severity) {
      case 'severe':
        return 'text-red-600 bg-red-100 dark:bg-red-900/30 dark:text-red-200';
      case 'moderate':
        return 'text-orange-600 bg-orange-100 dark:bg-orange-900/30 dark:text-orange-200';
      case 'mild':
        return 'text-yellow-600 bg-yellow-100 dark:bg-yellow-900/30 dark:text-yellow-200';
      default:
        return 'text-slate-600 bg-slate-100 dark:bg-slate-800 dark:text-slate-200';
    }
  };

  const getQueryStatusColor = (status: string) => {
    switch (status) {
      case 'open':
        return 'text-red-600 bg-red-100 dark:bg-red-900/30 dark:text-red-200';
      case 'answered':
        return 'text-blue-600 bg-blue-100 dark:bg-blue-900/30 dark:text-blue-200';
      case 'closed':
        return 'text-green-600 bg-green-100 dark:bg-green-900/30 dark:text-green-200';
      default:
        return 'text-slate-600 bg-slate-100 dark:bg-slate-800 dark:text-slate-200';
    }
  };

  const getPriorityColor = (priority: string) => {
    switch (priority) {
      case 'high':
        return 'text-red-600';
      case 'medium':
        return 'text-orange-600';
      case 'low':
        return 'text-slate-600';
      default:
        return 'text-slate-600';
    }
  };

  return (
    <div className="min-h-screen bg-slate-50 dark:bg-slate-900 p-6">
      <div className="max-w-7xl mx-auto space-y-6">
        {/* Breadcrumb Navigation */}
        <nav className="flex items-center gap-2 text-sm text-slate-600 dark:text-slate-400">
          <Link to="/portfolio" className="hover:text-indigo-600 dark:hover:text-indigo-400">
            Portfolio
          </Link>
          <span>→</span>
          {studyId && (
            <>
              <Link
                to={`/studies/${studyId}`}
                className="hover:text-indigo-600 dark:hover:text-indigo-400"
              >
                {studyId}
              </Link>
              <span>→</span>
            </>
          )}
          {siteId && (
            <>
              <Link
                to={`/studies/${studyId}/sites/${siteId}`}
                className="hover:text-indigo-600 dark:hover:text-indigo-400"
              >
                {siteId}
              </Link>
              <span>→</span>
            </>
          )}
          <span className="text-slate-900 dark:text-white font-medium">{patient.patient_id}</span>
        </nav>

        {/* Patient Header */}
        <div className="bg-white dark:bg-slate-800 p-6 rounded-xl shadow-sm border border-slate-200 dark:border-slate-700">
          <div className="flex items-start justify-between">
            <div>
              <div className="flex items-center gap-3 mb-2">
                <h1 className="text-3xl font-bold text-slate-900 dark:text-white">
                  {patient.patient_id}
                </h1>
                <span
                  className={cn(
                    'px-3 py-1 rounded-full text-xs font-semibold',
                    getStatusColor(patient.status)
                  )}
                >
                  {patient.status}
                </span>
              </div>
              <div className="space-y-1 text-sm text-slate-600 dark:text-slate-400">
                <div>
                  <span className="font-medium">Enrolled:</span>{' '}
                  {new Date(patient.enrollment_date).toLocaleDateString()}
                </div>
                <div>
                  <span className="font-medium">Last Visit:</span>{' '}
                  {new Date(patient.last_visit).toLocaleDateString()}
                </div>
              </div>
            </div>
            <div className="text-right">
              <div className="text-4xl font-bold text-slate-900 dark:text-white">
                {patient.visits_completed}/{patient.visits_total}
              </div>
              <div className="text-sm text-slate-500 dark:text-slate-400 font-medium">
                Visits Completed
              </div>
            </div>
          </div>
        </div>

        {/* Patient Metrics Cards */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <MetricCard
            title="Visits"
            value={`${patient.visits_completed}/${patient.visits_total}`}
            subtext={`${((patient.visits_completed / patient.visits_total) * 100).toFixed(0)}% complete`}
            icon="📅"
            color="blue"
          />
          <MetricCard
            title="SAEs"
            value={patient.saes.toString()}
            subtext={patient.saes > 0 ? 'Serious adverse events' : 'No SAEs reported'}
            icon="🚨"
            color={patient.saes > 0 ? 'red' : 'green'}
          />
          <MetricCard
            title="Queries"
            value={patient.queries.toString()}
            subtext={patient.queries > 0 ? 'Data queries' : 'No open queries'}
            icon="❓"
            color={patient.queries > 0 ? 'amber' : 'green'}
          />
        </div>

        {/* Visit Timeline */}
        <div className="bg-white dark:bg-slate-800 rounded-xl shadow-sm border border-slate-200 dark:border-slate-700 overflow-hidden">
          <div className="p-6 border-b border-slate-200 dark:border-slate-700">
            <h2 className="text-xl font-bold text-slate-900 dark:text-white">
              Visit Timeline
            </h2>
            <p className="text-sm text-slate-500 dark:text-slate-400 mt-1">
              Patient visit schedule and completion status
            </p>
          </div>

          <div className="p-6">
            <div className="relative">
              {/* Timeline line */}
              <div className="absolute left-8 top-0 bottom-0 w-0.5 bg-slate-200 dark:bg-slate-700"></div>

              {/* Visit items */}
              <div className="space-y-6">
                {visits.map((visit, index) => (
                  <div key={visit.visit_id} className="relative flex items-start gap-4">
                    {/* Timeline dot */}
                    <div className="relative z-10">
                      <div
                        className={cn(
                          'w-16 h-16 rounded-full flex items-center justify-center text-white font-bold text-sm',
                          getVisitStatusColor(visit.status)
                        )}
                      >
                        {visit.visit_id}
                      </div>
                    </div>

                    {/* Visit details */}
                    <div className="flex-1 bg-slate-50 dark:bg-slate-900 rounded-lg p-4">
                      <div className="flex items-start justify-between mb-2">
                        <div>
                          <h3 className="font-bold text-slate-900 dark:text-white">
                            {visit.visit_name}
                          </h3>
                          <p className="text-sm text-slate-600 dark:text-slate-400">
                            Scheduled: {new Date(visit.scheduled_date).toLocaleDateString()}
                          </p>
                          {visit.actual_date && (
                            <p className="text-sm text-slate-600 dark:text-slate-400">
                              Completed: {new Date(visit.actual_date).toLocaleDateString()}
                            </p>
                          )}
                        </div>
                        <span
                          className={cn(
                            'px-3 py-1 rounded-full text-xs font-semibold text-white',
                            getVisitStatusColor(visit.status)
                          )}
                        >
                          {visit.status.toUpperCase()}
                        </span>
                      </div>
                      <div className="flex items-center gap-2 text-sm text-slate-600 dark:text-slate-400">
                        <span>Forms:</span>
                        <div className="flex-1 bg-slate-200 dark:bg-slate-700 rounded-full h-2">
                          <div
                            className="bg-indigo-600 h-2 rounded-full transition-all"
                            style={{
                              width: `${(visit.forms_completed / visit.forms_total) * 100}%`
                            }}
                          ></div>
                        </div>
                        <span className="font-medium">
                          {visit.forms_completed}/{visit.forms_total}
                        </span>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </div>

        {/* SAEs Section */}
        {saes.length > 0 && (
          <div className="bg-white dark:bg-slate-800 rounded-xl shadow-sm border border-slate-200 dark:border-slate-700 overflow-hidden">
            <div className="p-6 border-b border-slate-200 dark:border-slate-700">
              <h2 className="text-xl font-bold text-slate-900 dark:text-white">
                Serious Adverse Events ({saes.length})
              </h2>
              <p className="text-sm text-slate-500 dark:text-slate-400 mt-1">
                Reported serious adverse events for this patient
              </p>
            </div>

            <div className="overflow-x-auto">
              <table className="w-full">
                <thead className="bg-slate-50 dark:bg-slate-900">
                  <tr>
                    <th className="px-6 py-3 text-left text-xs font-bold text-slate-500 dark:text-slate-400 uppercase tracking-wider">
                      SAE ID
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-bold text-slate-500 dark:text-slate-400 uppercase tracking-wider">
                      Event Term
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-bold text-slate-500 dark:text-slate-400 uppercase tracking-wider">
                      Onset Date
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-bold text-slate-500 dark:text-slate-400 uppercase tracking-wider">
                      Severity
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-bold text-slate-500 dark:text-slate-400 uppercase tracking-wider">
                      Outcome
                    </th>
                    <th className="px-6 py-3 text-right text-xs font-bold text-slate-500 dark:text-slate-400 uppercase tracking-wider">
                      Days to Report
                    </th>
                  </tr>
                </thead>
                <tbody className="bg-white dark:bg-slate-800 divide-y divide-slate-200 dark:divide-slate-700">
                  {saes.map((sae) => (
                    <tr key={sae.sae_id} className="hover:bg-slate-50 dark:hover:bg-slate-700/50 transition-colors">
                      <td className="px-6 py-4 whitespace-nowrap">
                        <div className="font-medium text-slate-900 dark:text-white">
                          {sae.sae_id}
                        </div>
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap">
                        <div className="text-slate-900 dark:text-white">{sae.event_term}</div>
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-slate-600 dark:text-slate-400">
                        {new Date(sae.onset_date).toLocaleDateString()}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap">
                        <span
                          className={cn(
                            'px-2 py-1 text-xs font-semibold rounded-full',
                            getSeverityColor(sae.severity)
                          )}
                        >
                          {sae.severity.toUpperCase()}
                        </span>
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-slate-600 dark:text-slate-400">
                        {sae.outcome}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-right">
                        <span
                          className={cn(
                            'font-medium',
                            sae.days_to_report > 2
                              ? 'text-red-600 dark:text-red-400'
                              : 'text-green-600 dark:text-green-400'
                          )}
                        >
                          {sae.days_to_report}
                        </span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}

        {/* Queries Section */}
        {queries.length > 0 && (
          <div className="bg-white dark:bg-slate-800 rounded-xl shadow-sm border border-slate-200 dark:border-slate-700 overflow-hidden">
            <div className="p-6 border-b border-slate-200 dark:border-slate-700">
              <h2 className="text-xl font-bold text-slate-900 dark:text-white">
                Data Queries ({queries.length})
              </h2>
              <p className="text-sm text-slate-500 dark:text-slate-400 mt-1">
                Data clarification queries for this patient
              </p>
            </div>

            <div className="overflow-x-auto">
              <table className="w-full">
                <thead className="bg-slate-50 dark:bg-slate-900">
                  <tr>
                    <th className="px-6 py-3 text-left text-xs font-bold text-slate-500 dark:text-slate-400 uppercase tracking-wider">
                      Query ID
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-bold text-slate-500 dark:text-slate-400 uppercase tracking-wider">
                      Form
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-bold text-slate-500 dark:text-slate-400 uppercase tracking-wider">
                      Field
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-bold text-slate-500 dark:text-slate-400 uppercase tracking-wider">
                      Query Text
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-bold text-slate-500 dark:text-slate-400 uppercase tracking-wider">
                      Status
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-bold text-slate-500 dark:text-slate-400 uppercase tracking-wider">
                      Priority
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-bold text-slate-500 dark:text-slate-400 uppercase tracking-wider">
                      Opened
                    </th>
                  </tr>
                </thead>
                <tbody className="bg-white dark:bg-slate-800 divide-y divide-slate-200 dark:divide-slate-700">
                  {queries.map((query) => (
                    <tr key={query.query_id} className="hover:bg-slate-50 dark:hover:bg-slate-700/50 transition-colors">
                      <td className="px-6 py-4 whitespace-nowrap">
                        <div className="font-medium text-slate-900 dark:text-white">
                          {query.query_id}
                        </div>
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-slate-900 dark:text-white">
                        {query.form}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-slate-600 dark:text-slate-400">
                        {query.field}
                      </td>
                      <td className="px-6 py-4 text-sm text-slate-600 dark:text-slate-400">
                        {query.query_text}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap">
                        <span
                          className={cn(
                            'px-2 py-1 text-xs font-semibold rounded-full',
                            getQueryStatusColor(query.status)
                          )}
                        >
                          {query.status.toUpperCase()}
                        </span>
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap">
                        <span className={cn('font-medium', getPriorityColor(query.priority))}>
                          {query.priority.toUpperCase()}
                        </span>
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-slate-600 dark:text-slate-400">
                        {new Date(query.opened_date).toLocaleDateString()}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}

        {/* Back Button */}
        <div className="flex justify-center">
          <button
            onClick={() => navigate(`/studies/${studyId}/sites/${siteId}`)}
            className="inline-flex items-center gap-2 px-6 py-3 bg-slate-600 text-white rounded-lg hover:bg-slate-700 transition-colors shadow-sm"
          >
            ← Back to Site
          </button>
        </div>
      </div>
    </div>
  );
}

// ========================================
// HELPER COMPONENTS
// ========================================

interface MetricCardProps {
  title: string;
  value: string;
  subtext: string;
  icon: string;
  color: 'blue' | 'green' | 'red' | 'amber';
}

function MetricCard({ title, value, subtext, icon, color }: MetricCardProps) {
  const colorClasses = {
    blue: 'from-blue-500 to-blue-600',
    green: 'from-green-500 to-green-600',
    red: 'from-red-500 to-red-600',
    amber: 'from-amber-500 to-amber-600',
  };

  return (
    <div
      className={cn(
        'bg-gradient-to-br p-6 rounded-xl text-white shadow-lg hover:shadow-xl transition-shadow',
        colorClasses[color]
      )}
    >
      <div className="flex items-center gap-4">
        <div className="text-4xl">{icon}</div>
        <div>
          <div className="text-3xl font-bold">{value}</div>
          <div className="text-sm opacity-90 uppercase tracking-wide font-medium">{title}</div>
          <div className="text-xs opacity-75 mt-1">{subtext}</div>
        </div>
      </div>
    </div>
  );
}
