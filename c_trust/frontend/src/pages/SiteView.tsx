/**
 * Site View Page
 * ==============
 * Displays site-level metrics, patient list, and drill-down navigation.
 * Part of multi-level drill-down: Portfolio → Study → Site → Patient
 */

import { useEffect, useState } from 'react';
import { useParams, useNavigate, useSearchParams, Link } from 'react-router-dom';
import { cn } from '@/lib/utils';

// ========================================
// TYPE DEFINITIONS
// ========================================

interface SiteDetail {
  site_id: string;
  site_name: string;
  enrollment: number;
  target_enrollment?: number;
  enrollment_rate?: number;
  saes: number;
  queries: number;
  open_queries: number;
  resolved_queries: number;
  risk_level: string;
  dqi_score: number;
  completeness_rate: number;
  last_data_entry?: string;
  patients: string[];
  data_quality_warning?: string;
}

interface PatientSummary {
  patient_id: string;
  enrollment_date: string;
  status: string;
  visits_completed: number;
  visits_total: number;
  saes: number;
  queries: number;
  last_visit: string;
}

// ========================================
// MAIN COMPONENT
// ========================================

export default function SiteView() {
  const { studyId, siteId } = useParams<{ studyId: string; siteId: string }>();
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const fromStudy = searchParams.get('from');

  const [site, setSite] = useState<SiteDetail | null>(null);
  const [patients, setPatients] = useState<PatientSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [retrying, setRetrying] = useState(false);
  const [dataQuality, setDataQuality] = useState<'complete' | 'partial' | 'unavailable'>('complete');

  useEffect(() => {
    if (siteId) {
      fetchSiteData();
    }
  }, [siteId]);

  const fetchSiteData = async () => {
    try {
      setLoading(true);
      setError(null);
      
      // Fetch site details
      const siteResponse = await fetch(
        `http://localhost:8000/api/v1/sites/${siteId}${studyId ? `?study_id=${studyId}` : ''}`
      );
      
      if (!siteResponse.ok) {
        if (siteResponse.status === 404) {
          throw new Error('Site not found. The site may not exist or data has not been loaded yet.');
        } else if (siteResponse.status === 500) {
          throw new Error('Server error while fetching site data. Please try again later.');
        } else {
          throw new Error(`Failed to fetch site data (Status: ${siteResponse.status})`);
        }
      }
      
      const siteData = await siteResponse.json();
      
      // Check for data quality warnings
      if (siteData.data_quality_warning) {
        setDataQuality('partial');
      }
      
      // Ensure patients array exists
      if (!siteData.patients || !Array.isArray(siteData.patients)) {
        siteData.patients = [];
        siteData.data_quality_warning = siteData.data_quality_warning || 'Patient data unavailable';
        setDataQuality('unavailable');
      }
      
      setSite(siteData);

      // Fetch patients - only if we have patient IDs
      if (siteData.patients && siteData.patients.length > 0) {
        try {
          const patientsResponse = await fetch(
            `http://localhost:8000/api/v1/sites/${siteId}/patients`
          );
          
          if (patientsResponse.ok) {
            const patientsData = await patientsResponse.json();
            setPatients(patientsData);
          } else {
            // Patient details unavailable, but we have IDs
            console.warn('Patient details unavailable, showing IDs only');
            setDataQuality('partial');
          }
        } catch (patientErr) {
          console.warn('Failed to fetch patient details:', patientErr);
          setDataQuality('partial');
        }
      } else {
        setPatients([]);
      }

      setError(null);
    } catch (err) {
      console.error('Error fetching site data:', err);
      setError(err instanceof Error ? err.message : 'Failed to load site data. Please try again.');
      setDataQuality('unavailable');
    } finally {
      setLoading(false);
      setRetrying(false);
    }
  };

  const handleRetry = () => {
    setRetrying(true);
    fetchSiteData();
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-slate-50 dark:bg-slate-900 p-6">
        <div className="max-w-7xl mx-auto">
          <div className="flex flex-col items-center justify-center min-h-[60vh] space-y-4">
            <div className="relative">
              <div className="w-16 h-16 border-4 border-indigo-200 dark:border-indigo-900 rounded-full"></div>
              <div className="w-16 h-16 border-4 border-indigo-600 border-t-transparent rounded-full animate-spin absolute top-0 left-0"></div>
            </div>
            <div className="text-center">
              <h3 className="text-lg font-semibold text-slate-900 dark:text-white mb-1">
                {retrying ? 'Retrying...' : 'Loading Site Data'}
              </h3>
              <p className="text-sm text-slate-500 dark:text-slate-400">
                Fetching site details and patient information
              </p>
            </div>
          </div>
        </div>
      </div>
    );
  }

  if (error || !site) {
    return (
      <div className="min-h-screen bg-slate-50 dark:bg-slate-900 p-6">
        <div className="max-w-7xl mx-auto">
          <div className="max-w-2xl mx-auto mt-12">
            <div className="bg-red-50 dark:bg-red-900/20 border-2 border-red-200 dark:border-red-800 rounded-xl p-8 shadow-lg">
              <div className="flex items-start gap-4">
                <div className="flex-shrink-0">
                  <div className="w-12 h-12 bg-red-100 dark:bg-red-900/40 rounded-full flex items-center justify-center">
                    <span className="text-2xl">⚠️</span>
                  </div>
                </div>
                <div className="flex-1">
                  <h2 className="text-xl font-bold text-red-800 dark:text-red-200 mb-2">
                    Unable to Load Site Data
                  </h2>
                  <p className="text-red-700 dark:text-red-300 mb-4">
                    {error || 'Site not found or data unavailable'}
                  </p>
                  
                  <div className="bg-red-100 dark:bg-red-900/30 rounded-lg p-4 mb-4">
                    <h3 className="text-sm font-semibold text-red-800 dark:text-red-200 mb-2">
                      Possible reasons:
                    </h3>
                    <ul className="text-sm text-red-700 dark:text-red-300 space-y-1 list-disc list-inside">
                      <li>Site data has not been loaded into the system yet</li>
                      <li>Data extraction from NEST files failed</li>
                      <li>Network connection issue</li>
                      <li>Invalid site ID or study ID</li>
                    </ul>
                  </div>

                  <div className="flex gap-3">
                    <button
                      onClick={handleRetry}
                      disabled={retrying}
                      className="inline-flex items-center gap-2 px-4 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700 transition-colors disabled:opacity-50 disabled:cursor-not-allowed shadow-sm"
                    >
                      {retrying ? (
                        <>
                          <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin"></div>
                          Retrying...
                        </>
                      ) : (
                        <>
                          🔄 Retry
                        </>
                      )}
                    </button>
                    <button
                      onClick={() => navigate(fromStudy ? `/studies/${fromStudy}` : '/portfolio')}
                      className="inline-flex items-center gap-2 px-4 py-2 bg-slate-600 text-white rounded-lg hover:bg-slate-700 transition-colors shadow-sm"
                    >
                      ← Go Back
                    </button>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    );
  }

  const getRiskColor = (risk: string) => {
    switch (risk.toLowerCase()) {
      case 'critical':
        return 'bg-red-500';
      case 'high':
        return 'bg-orange-500';
      case 'medium':
        return 'bg-yellow-500';
      case 'low':
        return 'bg-green-500';
      default:
        return 'bg-slate-500';
    }
  };

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

  return (
    <div className="min-h-screen bg-slate-50 dark:bg-slate-900 p-6">
      <div className="max-w-7xl mx-auto space-y-6">
        {/* Breadcrumb Navigation */}
        <nav className="flex items-center gap-2 text-sm text-slate-600 dark:text-slate-400">
          <Link to="/portfolio" className="hover:text-indigo-600 dark:hover:text-indigo-400">
            Portfolio
          </Link>
          <span>→</span>
          {fromStudy && (
            <>
              <Link
                to={`/studies/${fromStudy}`}
                className="hover:text-indigo-600 dark:hover:text-indigo-400"
              >
                {fromStudy}
              </Link>
              <span>→</span>
            </>
          )}
          <span className="text-slate-900 dark:text-white font-medium">{site.site_id}</span>
        </nav>

        {/* Site Header */}
        <div className="bg-white dark:bg-slate-800 p-6 rounded-xl shadow-sm border border-slate-200 dark:border-slate-700">
          <div className="flex items-start justify-between">
            <div>
              <div className="flex items-center gap-3 mb-2">
                <h1 className="text-3xl font-bold text-slate-900 dark:text-white">
                  {site.site_name}
                </h1>
                <span
                  className={cn(
                    'px-3 py-1 rounded-full text-xs font-bold uppercase text-white',
                    getRiskColor(site.risk_level)
                  )}
                >
                  {site.risk_level}
                </span>
              </div>
              <div className="text-slate-500 dark:text-slate-400 font-medium">
                Site ID: {site.site_id}
              </div>
              {site.last_data_entry && (
                <div className="mt-2 text-sm text-slate-400">
                  Last data entry: {new Date(site.last_data_entry).toLocaleDateString()}
                </div>
              )}
            </div>
            <div className="text-right">
              <div className="text-4xl font-bold text-slate-900 dark:text-white">
                {site.dqi_score.toFixed(1)}
              </div>
              <div className="text-sm text-slate-500 dark:text-slate-400 font-medium">
                Site DQI Score
              </div>
            </div>
          </div>
        </div>

        {/* Data Quality Warning Banner */}
        {(site.data_quality_warning || dataQuality !== 'complete') && (
          <div className="bg-amber-50 dark:bg-amber-900/20 border-l-4 border-amber-500 p-4 rounded-lg">
            <div className="flex items-start gap-3">
              <div className="flex-shrink-0">
                <span className="text-2xl">⚠️</span>
              </div>
              <div className="flex-1">
                <h3 className="text-sm font-semibold text-amber-800 dark:text-amber-200 mb-1">
                  Data Quality Notice
                </h3>
                <p className="text-sm text-amber-700 dark:text-amber-300">
                  {site.data_quality_warning || 
                    (dataQuality === 'partial' 
                      ? 'Some patient data is unavailable. Displaying available information only.' 
                      : 'Patient data extraction incomplete. Some information may be missing.')}
                </p>
                {site.enrollment > 0 && (!site.patients || site.patients.length === 0) && (
                  <p className="text-sm text-amber-700 dark:text-amber-300 mt-2">
                    <strong>{site.enrollment} patients enrolled</strong>, but patient IDs are unavailable. 
                    This may be due to CPID data extraction issues.
                  </p>
                )}
              </div>
              <button
                onClick={handleRetry}
                disabled={retrying}
                className="flex-shrink-0 px-3 py-1 text-xs font-medium text-amber-800 dark:text-amber-200 bg-amber-100 dark:bg-amber-900/40 rounded hover:bg-amber-200 dark:hover:bg-amber-900/60 transition-colors disabled:opacity-50"
              >
                {retrying ? 'Refreshing...' : 'Refresh Data'}
              </button>
            </div>
          </div>
        )}

        {/* Site Metrics Cards */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
          <MetricCard
            title="Enrollment"
            value={site.enrollment.toString()}
            subtext={
              site.target_enrollment
                ? `Target: ${site.target_enrollment} (${site.enrollment_rate?.toFixed(0)}%)`
                : 'Patients enrolled'
            }
            icon="👥"
            color="blue"
          />
          <MetricCard
            title="SAEs"
            value={site.saes.toString()}
            subtext="Serious adverse events"
            icon="🚨"
            color={site.saes > 0 ? 'red' : 'green'}
          />
          <MetricCard
            title="Open Queries"
            value={site.open_queries.toString()}
            subtext={`${site.resolved_queries} resolved`}
            icon="❓"
            color={site.open_queries > 10 ? 'amber' : 'green'}
          />
          <MetricCard
            title="Completeness"
            value={`${(site.completeness_rate * 100).toFixed(0)}%`}
            subtext="Data completeness rate"
            icon="📊"
            color={site.completeness_rate > 0.9 ? 'green' : 'amber'}
          />
        </div>

        {/* Patient Table */}
        <div className="bg-white dark:bg-slate-800 rounded-xl shadow-sm border border-slate-200 dark:border-slate-700 overflow-hidden">
          <div className="p-6 border-b border-slate-200 dark:border-slate-700">
            <div className="flex items-center justify-between">
              <div>
                <h2 className="text-xl font-bold text-slate-900 dark:text-white">
                  Patients ({site.patients?.length || 0})
                </h2>
                <p className="text-sm text-slate-500 dark:text-slate-400 mt-1">
                  {patients.length > 0 
                    ? 'Patient enrollment and visit tracking'
                    : site.patients?.length > 0
                      ? 'Patient IDs available (detailed data unavailable)'
                      : 'No patient data available'}
                </p>
              </div>
              <button className="px-4 py-2 bg-indigo-600 text-white rounded-lg hover:bg-indigo-700 transition-colors text-sm font-medium">
                Export Patient List
              </button>
            </div>
          </div>

          <div className="overflow-x-auto">
            {patients.length > 0 ? (
              <table className="w-full">
                <thead className="bg-slate-50 dark:bg-slate-900">
                  <tr>
                    <th className="px-6 py-3 text-left text-xs font-bold text-slate-500 dark:text-slate-400 uppercase tracking-wider">
                      Patient ID
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-bold text-slate-500 dark:text-slate-400 uppercase tracking-wider">
                      Status
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-bold text-slate-500 dark:text-slate-400 uppercase tracking-wider">
                      Enrollment Date
                    </th>
                    <th className="px-6 py-3 text-right text-xs font-bold text-slate-500 dark:text-slate-400 uppercase tracking-wider">
                      Visits
                    </th>
                    <th className="px-6 py-3 text-right text-xs font-bold text-slate-500 dark:text-slate-400 uppercase tracking-wider">
                      SAEs
                    </th>
                    <th className="px-6 py-3 text-right text-xs font-bold text-slate-500 dark:text-slate-400 uppercase tracking-wider">
                      Queries
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-bold text-slate-500 dark:text-slate-400 uppercase tracking-wider">
                      Last Visit
                    </th>
                    <th className="px-6 py-3 text-right text-xs font-bold text-slate-500 dark:text-slate-400 uppercase tracking-wider">
                      Action
                    </th>
                  </tr>
                </thead>
                <tbody className="bg-white dark:bg-slate-800 divide-y divide-slate-200 dark:divide-slate-700">
                  {patients.map((patient) => (
                    <tr
                      key={patient.patient_id}
                      className="hover:bg-slate-50 dark:hover:bg-slate-700/50 transition-colors"
                    >
                      <td className="px-6 py-4 whitespace-nowrap">
                        <div className="font-medium text-slate-900 dark:text-white">
                          {patient.patient_id}
                        </div>
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap">
                        <span
                          className={cn(
                            'px-2 py-1 text-xs font-semibold rounded-full',
                            getStatusColor(patient.status)
                          )}
                        >
                          {patient.status}
                        </span>
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-slate-600 dark:text-slate-400">
                        {new Date(patient.enrollment_date).toLocaleDateString()}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-right text-sm text-slate-900 dark:text-white">
                        {patient.visits_completed}/{patient.visits_total}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-right">
                        <span
                          className={cn(
                            'font-medium',
                            patient.saes > 0
                              ? 'text-red-600 dark:text-red-400'
                              : 'text-slate-500 dark:text-slate-400'
                          )}
                        >
                          {patient.saes}
                        </span>
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-right">
                        <span
                          className={cn(
                            'font-medium',
                            patient.queries > 0
                              ? 'text-amber-600 dark:text-amber-400'
                              : 'text-slate-500 dark:text-slate-400'
                          )}
                        >
                          {patient.queries}
                        </span>
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-slate-600 dark:text-slate-400">
                        {new Date(patient.last_visit).toLocaleDateString()}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-right text-sm">
                        <button
                          onClick={() =>
                            navigate(
                              `/studies/${studyId}/sites/${siteId}/patients/${patient.patient_id}`
                            )
                          }
                          className="text-indigo-600 hover:text-indigo-900 dark:text-indigo-400 dark:hover:text-indigo-300 font-medium"
                        >
                          View Details →
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            ) : site.patients && site.patients.length > 0 ? (
              // We have patient IDs but no detailed data
              <div className="p-8">
                <div className="bg-amber-50 dark:bg-amber-900/20 border border-amber-200 dark:border-amber-800 rounded-lg p-6">
                  <div className="flex items-start gap-4">
                    <div className="text-3xl">👥</div>
                    <div className="flex-1">
                      <h3 className="text-lg font-semibold text-amber-900 dark:text-amber-100 mb-2">
                        Patient IDs Available
                      </h3>
                      <p className="text-sm text-amber-800 dark:text-amber-200 mb-4">
                        {site.patients.length} patient(s) enrolled, but detailed information is currently unavailable.
                      </p>
                      <div className="bg-white dark:bg-slate-800 rounded-lg p-4 mb-4">
                        <h4 className="text-sm font-semibold text-slate-900 dark:text-white mb-2">
                          Enrolled Patients:
                        </h4>
                        <div className="flex flex-wrap gap-2">
                          {site.patients.map((patientId) => (
                            <span
                              key={patientId}
                              className="px-3 py-1 bg-slate-100 dark:bg-slate-700 text-slate-700 dark:text-slate-300 rounded-full text-sm font-medium"
                            >
                              {patientId}
                            </span>
                          ))}
                        </div>
                      </div>
                      <button
                        onClick={handleRetry}
                        disabled={retrying}
                        className="inline-flex items-center gap-2 px-4 py-2 bg-amber-600 text-white rounded-lg hover:bg-amber-700 transition-colors disabled:opacity-50 text-sm font-medium"
                      >
                        {retrying ? (
                          <>
                            <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin"></div>
                            Refreshing...
                          </>
                        ) : (
                          <>
                            🔄 Refresh Patient Data
                          </>
                        )}
                      </button>
                    </div>
                  </div>
                </div>
              </div>
            ) : (
              // No patient data at all
              <div className="p-12 text-center">
                <div className="text-6xl mb-4">📋</div>
                <h3 className="text-lg font-semibold text-slate-900 dark:text-white mb-2">
                  No Patients Enrolled
                </h3>
                <p className="text-slate-500 dark:text-slate-400 mb-4">
                  {site.enrollment > 0 
                    ? `Expected ${site.enrollment} patient(s), but data is unavailable`
                    : 'No patients have been enrolled at this site yet'}
                </p>
                {site.enrollment > 0 && (
                  <button
                    onClick={handleRetry}
                    disabled={retrying}
                    className="inline-flex items-center gap-2 px-4 py-2 bg-indigo-600 text-white rounded-lg hover:bg-indigo-700 transition-colors disabled:opacity-50 text-sm font-medium"
                  >
                    {retrying ? (
                      <>
                        <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin"></div>
                        Refreshing...
                      </>
                    ) : (
                      <>
                        🔄 Refresh Data
                      </>
                    )}
                  </button>
                )}
              </div>
            )}
          </div>
        </div>

        {/* Back Button */}
        <div className="flex justify-center">
          <button
            onClick={() => navigate(fromStudy ? `/studies/${fromStudy}` : '/portfolio')}
            className="inline-flex items-center gap-2 px-6 py-3 bg-slate-600 text-white rounded-lg hover:bg-slate-700 transition-colors shadow-sm"
          >
            ← Back to {fromStudy ? 'Study' : 'Portfolio'}
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
