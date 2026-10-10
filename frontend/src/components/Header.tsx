'use client';

import React from 'react';
import { Activity, ShieldCheck, RefreshCw } from 'lucide-react';
import { UserSession } from '@/lib/types';

interface HeaderProps {
  currentSession: UserSession;
  onOpenLoginModal: () => void;
}

export const Header: React.FC<HeaderProps> = ({ currentSession, onOpenLoginModal }) => {
  return (
    <header className="h-16 bg-slate-900/80 backdrop-blur-md border-b border-slate-800 px-6 flex items-center justify-between sticky top-0 z-20">
      {/* Brand & Subtitle */}
      <div className="flex items-center gap-3">
        <div className="w-10 h-10 rounded-xl bg-gradient-to-tr from-blue-600 to-indigo-500 flex items-center justify-center shadow-lg shadow-blue-500/20">
          <Activity className="w-6 h-6 text-white" />
        </div>
        <div>
          <div className="flex items-center gap-2">
            <h1 className="font-bold text-slate-100 text-lg tracking-tight">MediBot</h1>
            <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-blue-500/10 text-blue-400 border border-blue-500/20 font-semibold">
              v1.0 Advanced RAG
            </span>
          </div>
          <p className="text-xs text-slate-400">MediAssist Health Network • RBAC Enforced Intelligent Assistant</p>
        </div>
      </div>

      {/* Right Header Status Controls */}
      <div className="flex items-center gap-4">
        <div className="hidden sm:flex items-center gap-2 px-3 py-1.5 rounded-full bg-slate-950/60 border border-slate-800 text-xs">
          <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse" />
          <span className="text-slate-300 font-medium">Qdrant Vector Store Connected</span>
        </div>

        <button
          onClick={onOpenLoginModal}
          className="flex items-center gap-2 px-3.5 py-1.5 rounded-lg bg-slate-800/80 hover:bg-slate-700/80 border border-slate-700 text-xs text-slate-200 font-medium transition-all"
        >
          <ShieldCheck className="w-4 h-4 text-emerald-400" />
          <span>Role: <span className="font-mono text-emerald-300">{currentSession.role}</span></span>
          <RefreshCw className="w-3 h-3 text-slate-400 ml-1" />
        </button>
      </div>
    </header>
  );
};
