// C-TRUST Dashboard - Main Application
// ========================================
import { BrowserRouter, Routes, Route } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import Layout from '@/components/layout/Layout';
import Portfolio from '@/pages/Portfolio';
import StudyDashboard from '@/pages/StudyDashboard';
import SiteDetail from '@/pages/SiteDetail';
import Analytics from '@/pages/Analytics';
import AIInsights from '@/pages/AIInsights';
import Notifications from '@/pages/Notifications';
import Settings from '@/pages/Settings';
import { ErrorBoundary } from '@/components/ui/ErrorBoundary';
import { ToastProvider } from '@/components/ui/Toast';
import { OfflineIndicator } from '@/components/ui/OfflineIndicator';
import { RoleProvider } from '@/contexts/RoleContext';

// Lazy load Guardian Dashboard (new feature)
import { Suspense, lazy } from 'react';
const GuardianDashboard = lazy(() => import('@/pages/GuardianDashboard'));

// Import new AI Insights page (Task 3.2)
import AIInsightsNew from '@/pages/AIInsightsNew';

// Import Site View page (Task 5.2)
import SiteView from '@/pages/SiteView';

// Import Patient View page (Task 5.3)
import PatientView from '@/pages/PatientView';

// Create React Query client
const queryClient = new QueryClient({
    defaultOptions: {
        queries: {
            staleTime: 5 * 60 * 1000, // 5 minutes
            retry: 2,
            refetchOnWindowFocus: false,
        },
    },
});

// Loading fallback for lazy-loaded components
const PageLoader = () => (
    <div style={{
        display: 'flex',
        justifyContent: 'center',
        alignItems: 'center',
        height: '50vh',
        color: '#888',
    }}>
        Loading...
    </div>
);

function App() {
    return (
        <QueryClientProvider client={queryClient}>
            <RoleProvider defaultRole="STUDY_LEAD">
                <ToastProvider>
                    <ErrorBoundary>
                        <BrowserRouter>
                            <OfflineIndicator />
                            <Layout>
                                <Suspense fallback={<PageLoader />}>
                                    <Routes>
                                        <Route path="/" element={<Portfolio />} />
                                        <Route path="/portfolio" element={<Portfolio />} />
                                        <Route path="/studies/:id" element={<StudyDashboard />} />
                                        <Route path="/studies/:studyId/sites/:siteId" element={<SiteView />} />
                                        <Route path="/studies/:studyId/sites/:siteId/patients/:patientId" element={<PatientView />} />
                                        <Route path="/analytics" element={<Analytics />} />
                                        <Route path="/ai-insights" element={<AIInsights />} />
                                        <Route path="/insights/:studyId" element={<AIInsightsNew />} />
                                        <Route path="/notifications" element={<Notifications />} />
                                        <Route path="/settings" element={<Settings />} />
                                        <Route path="/guardian" element={<GuardianDashboard />} />
                                    </Routes>
                                </Suspense>
                            </Layout>
                        </BrowserRouter>
                    </ErrorBoundary>
                </ToastProvider>
            </RoleProvider>
        </QueryClientProvider>
    );
}

export default App;

