import React from 'react';
import { Sidebar } from './Sidebar';
import { TopBar } from './TopBar';
import { Banner } from '../common/Banner';

export const AppShell: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  return (
    <div style={{ display: 'flex', minHeight: '100vh', background: 'var(--bg-dark)' }}>
      {/* Sidebar */}
      <Sidebar />

      {/* Main Content Area */}
      <div style={{
        flex: 1,
        marginLeft: 'var(--sidebar-width)',
        display: 'flex',
        flexDirection: 'column',
        minWidth: 0
      }}>
        {/* Top Navbar */}
        <TopBar />

        {/* Global Connection / Demo Banner */}
        <Banner />

        {/* Page Body */}
        <main style={{ flex: 1, padding: '24px', overflowY: 'auto' }}>
          {children}
        </main>
      </div>
    </div>
  );
};
