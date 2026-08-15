import { useState, useEffect } from 'react';

export interface RouteParams {
  sessionId?: string;
}

export interface RouterState {
  path: string;
  params: RouteParams;
}

export function parseRoute(pathname: string): RouterState {
  const cleanPath = pathname.split('?')[0];

  // Route matchers: /app/traces/:id
  const traceMatch = cleanPath.match(/^\/app\/traces\/([^\/]+)$/);
  if (traceMatch) {
    return { path: '/app/traces/:sessionId', params: { sessionId: traceMatch[1] } };
  }

  // Route matchers: /app/root-cause/:id
  const rootCauseMatch = cleanPath.match(/^\/app\/root-cause\/([^\/]+)$/);
  if (rootCauseMatch) {
    return { path: '/app/root-cause/:sessionId', params: { sessionId: rootCauseMatch[1] } };
  }

  // Exact paths
  if (cleanPath === '' || cleanPath === '/') return { path: '/', params: {} };
  if (cleanPath === '/demo') return { path: '/demo', params: {} };
  if (cleanPath === '/how-it-works') return { path: '/how-it-works', params: {} };
  if (cleanPath === '/docs') return { path: '/docs', params: {} };

  if (cleanPath.startsWith('/app')) {
    return { path: cleanPath, params: {} };
  }

  return { path: '/', params: {} };
}

export function navigate(url: string) {
  window.history.pushState({}, '', url);
  window.dispatchEvent(new Event('popstate'));
}

export const useLocation = () => {
  const [routeState, setRouteState] = useState<RouterState>(() => parseRoute(window.location.pathname));

  useEffect(() => {
    const handlePopState = () => {
      setRouteState(parseRoute(window.location.pathname));
    };
    window.addEventListener('popstate', handlePopState);
    return () => window.removeEventListener('popstate', handlePopState);
  }, []);

  return {
    pathname: window.location.pathname,
    route: routeState.path,
    params: routeState.params,
    navigate
  };
};
