import React, { createContext, useContext, useState, useEffect } from 'react';
import type { AppEnvironment } from '../types';
import { fetchHealth } from '../services/api';

interface AppContextType {
  apiKey: string | null;
  setApiKey: (key: string | null) => void;
  environment: AppEnvironment;
  setEnvironment: (env: AppEnvironment) => void;
  isDemoMode: boolean;
  setIsDemoMode: (demo: boolean) => void;
  currentProject: string;
  setCurrentProject: (proj: string) => void;
  backendConnected: boolean | null;
  backendInfo: { service?: string; database_backend?: string; database_configured?: boolean } | null;
  refreshHealth: () => Promise<void>;
}

const AppContext = createContext<AppContextType | undefined>(undefined);

export const AppProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [apiKey, setApiKeyState] = useState<string | null>(() => {
    return localStorage.getItem('agenteval_api_key') || null;
  });

  const [environment, setEnvironment] = useState<AppEnvironment>('development');
  
  const [isDemoMode, setIsDemoModeState] = useState<boolean>(() => {
    const envDemo = import.meta.env.VITE_DEMO_MODE === 'true';
    const localDemo = localStorage.getItem('agenteval_demo_mode') === 'true';
    return envDemo || localDemo || window.location.pathname.startsWith('/demo');
  });

  const [currentProject, setCurrentProject] = useState<string>('Default Project');
  const [backendConnected, setBackendConnected] = useState<boolean | null>(null);
  const [backendInfo, setBackendInfo] = useState<any>(null);

  const setApiKey = (key: string | null) => {
    if (key) {
      localStorage.setItem('agenteval_api_key', key);
    } else {
      localStorage.removeItem('agenteval_api_key');
    }
    setApiKeyState(key);
  };

  const setIsDemoMode = (demo: boolean) => {
    localStorage.setItem('agenteval_demo_mode', demo ? 'true' : 'false');
    setIsDemoModeState(demo);
  };

  const refreshHealth = async () => {
    try {
      const data = await fetchHealth();
      setBackendConnected(true);
      setBackendInfo(data);
    } catch (_) {
      setBackendConnected(false);
      setBackendInfo(null);
    }
  };

  useEffect(() => {
    refreshHealth();
  }, []);

  return (
    <AppContext.Provider
      value={{
        apiKey,
        setApiKey,
        environment,
        setEnvironment,
        isDemoMode,
        setIsDemoMode,
        currentProject,
        setCurrentProject,
        backendConnected,
        backendInfo,
        refreshHealth
      }}
    >
      {children}
    </AppContext.Provider>
  );
};

export const useApp = () => {
  const context = useContext(AppContext);
  if (!context) {
    throw new Error('useApp must be used within an AppProvider');
  }
  return context;
};
