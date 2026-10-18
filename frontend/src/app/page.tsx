'use client';

import React, { useState, useEffect, useCallback } from 'react';
import { Role, UserSession } from '@/lib/types';
import { fetchAccessibleCollections, loginUser } from '@/lib/api';
import { Header } from '@/components/Header';
import { Sidebar, DEMO_ROLES } from '@/components/Sidebar';
import { ChatInterface } from '@/components/ChatInterface';
import { LoginModal } from '@/components/LoginModal';

const INITIAL_SESSION: UserSession = {
  username: 'dr.mehta',
  role: 'doctor',
  name: 'Dr. Rajesh Mehta',
  dept: 'Clinical Dept',
  token: ''
};

export default function Home() {
  const [currentSession, setCurrentSession] = useState<UserSession>(INITIAL_SESSION);
  const [accessibleCollections, setAccessibleCollections] = useState<string[]>(['clinical', 'nursing', 'general']);
  const [sqlRagPermitted, setSqlRagPermitted] = useState<boolean>(false);
  const [isLoginModalOpen, setIsLoginModalOpen] = useState<boolean>(false);
  const [authNotice, setAuthNotice] = useState<string>('');

  // Fetch collections whenever role changes
  useEffect(() => {
    async function loadPermissions() {
      if (!currentSession.token) return;
      try {
        const res = await fetchAccessibleCollections(currentSession.role, currentSession.token);
        setAccessibleCollections(res.collections || []);
        setSqlRagPermitted(res.sql_rag_permitted || false);
      } catch (err) {
        console.error('Failed to load role permissions:', err);
      }
    }
    loadPermissions();
  }, [currentSession.role, currentSession.token]);

  // Every session must carry a backend-issued token; on failure, keep the current session and ask the user to log in
  const signInAs = useCallback(async (newRole: Role) => {
    const demo = DEMO_ROLES.find((d) => d.role === newRole);
    if (!demo) return;
    try {
      const session = await loginUser(demo.username, newRole);
      setCurrentSession(session);
      setAuthNotice('');
    } catch (err) {
      const reason = err instanceof Error ? err.message : 'Login failed';
      setAuthNotice(`Could not sign in as ${demo.label}: ${reason}. Authenticate to continue.`);
      setIsLoginModalOpen(true);
    }
  }, []);

  useEffect(() => {
    signInAs('doctor');
  }, [signInAs]);

  return (
    <div className="h-screen w-screen bg-slate-950 text-slate-100 flex flex-col overflow-hidden font-sans">
      <Header
        currentSession={currentSession}
        onOpenLoginModal={() => setIsLoginModalOpen(true)}
      />

      <div className="flex-1 flex overflow-hidden">
        <Sidebar
          currentSession={currentSession}
          onSwitchRole={signInAs}
          accessibleCollections={accessibleCollections}
          sqlRagPermitted={sqlRagPermitted}
        />

        <main className="flex-1 flex flex-col overflow-hidden">
          <ChatInterface currentSession={currentSession} />
        </main>
      </div>

      <LoginModal
        isOpen={isLoginModalOpen}
        notice={authNotice}
        onClose={() => {
          setIsLoginModalOpen(false);
          setAuthNotice('');
        }}
        onLoginSuccess={(session) => {
          setCurrentSession(session);
          setAuthNotice('');
        }}
      />
    </div>
  );
}
