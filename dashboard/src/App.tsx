import React, { useEffect } from 'react';
import { AppProvider, useApp } from './context/AppContext';
import { useLocation } from './router';
import { AppShell } from './components/layout/AppShell';

// Public Pages
import { LandingPage } from './pages/public/LandingPage';
import { DocsPage } from './pages/public/DocsPage';
import { HowItWorksPage } from './pages/public/HowItWorksPage';

// App Pages
import { OverviewPage } from './pages/app/OverviewPage';
import { TracesPage } from './pages/app/TracesPage';
import { TraceDetailPage } from './pages/app/TraceDetailPage';
import { RootCausePage } from './pages/app/RootCausePage';
import { EvaluationsPage } from './pages/app/EvaluationsPage';
import { BenchmarksPage } from './pages/app/BenchmarksPage';
import { IntegrationsPage } from './pages/app/IntegrationsPage';
import { ApiKeysPage } from './pages/app/ApiKeysPage';
import { AnalyticsPage } from './pages/app/AnalyticsPage';
import { ProjectsPage } from './pages/app/ProjectsPage';
import { SettingsPage } from './pages/app/SettingsPage';

const AppContent: React.FC = () => {
  const { route, params } = useLocation();
  const { setIsDemoMode } = useApp();

  // If navigating to /demo explicitly, turn on demo mode
  useEffect(() => {
    if (route === '/demo') {
      setIsDemoMode(true);
    }
  }, [route, setIsDemoMode]);

  // Public standalone pages (No sidebar shell)
  if (route === '/') {
    return <LandingPage />;
  }
  if (route === '/docs') {
    return <DocsPage />;
  }
  if (route === '/how-it-works') {
    return <HowItWorksPage />;
  }

  // Dashboard Application Pages (Inside AppShell)
  let pageComponent = <OverviewPage />;

  if (route === '/demo' || route === '/app' || route === '/app/overview') {
    pageComponent = <OverviewPage />;
  } else if (route === '/app/traces') {
    pageComponent = <TracesPage />;
  } else if (route === '/app/traces/:sessionId') {
    pageComponent = <TraceDetailPage sessionId={params.sessionId} />;
  } else if (route === '/app/root-cause/:sessionId') {
    pageComponent = <RootCausePage sessionId={params.sessionId} />;
  } else if (route === '/app/evaluations') {
    pageComponent = <EvaluationsPage />;
  } else if (route === '/app/benchmarks') {
    pageComponent = <BenchmarksPage />;
  } else if (route === '/app/integrations') {
    pageComponent = <IntegrationsPage />;
  } else if (route === '/app/api-keys') {
    pageComponent = <ApiKeysPage />;
  } else if (route === '/app/analytics') {
    pageComponent = <AnalyticsPage />;
  } else if (route === '/app/projects') {
    pageComponent = <ProjectsPage />;
  } else if (route === '/app/settings') {
    pageComponent = <SettingsPage />;
  }

  return <AppShell>{pageComponent}</AppShell>;
};

export default function App() {
  return (
    <AppProvider>
      <AppContent />
    </AppProvider>
  );
}
