'use client';

import React from 'react';
import { Role, UserSession } from '@/lib/types';
import { 
  Stethoscope, 
  HeartPulse, 
  Receipt, 
  Wrench, 
  ShieldCheck, 
  Database, 
  FileText, 
  Lock,
  CheckCircle2
} from 'lucide-react';

interface SidebarProps {
  currentSession: UserSession;
  onSwitchRole: (role: Role) => void;
  accessibleCollections: string[];
  sqlRagPermitted: boolean;
}

export const DEMO_ROLES: { role: Role; username: string; label: string; name: string; dept: string; color: string; icon: React.ReactNode }[] = [
  { 
    role: 'doctor', 
    username: 'dr.mehta', 
    label: 'Doctor', 
    name: 'Dr. Rajesh Mehta', 
    dept: 'Clinical Dept',
    color: 'emerald',
    icon: <Stethoscope className="w-5 h-5 text-emerald-400" />
  },
  { 
    role: 'nurse', 
    username: 'nurse.priya', 
    label: 'Nurse', 
    name: 'Priya Sharma (RN)', 
    dept: 'Nursing Care',
    color: 'cyan',
    icon: <HeartPulse className="w-5 h-5 text-cyan-400" />
  },
  { 
    role: 'billing_executive', 
    username: 'billing.ravi', 
    label: 'Billing Executive', 
    name: 'Ravi Teja', 
    dept: 'Billing & Insurance',
    color: 'indigo',
    icon: <Receipt className="w-5 h-5 text-indigo-400" />
  },
  { 
    role: 'technician', 
    username: 'tech.anand', 
    label: 'Technician', 
    name: 'Anand Verma', 
    dept: 'Medical Equipment',
    color: 'amber',
    icon: <Wrench className="w-5 h-5 text-amber-400" />
  },
  { 
    role: 'admin', 
    username: 'admin.sys', 
    label: 'System Admin', 
    name: 'System Administrator', 
    dept: 'Executive / IT',
    color: 'purple',
    icon: <ShieldCheck className="w-5 h-5 text-purple-400" />
  }
];

export const Sidebar: React.FC<SidebarProps> = ({
  currentSession,
  onSwitchRole,
  accessibleCollections,
  sqlRagPermitted
}) => {
  return (
    <aside className="w-80 bg-slate-900/90 backdrop-blur-xl border-r border-slate-800/80 flex flex-col h-full overflow-y-auto">
      {/* Current Active Account Section */}
      <div className="p-5 border-b border-slate-800/80 bg-slate-950/40">
        <div className="text-xs font-semibold tracking-wider text-slate-400 uppercase mb-3 flex items-center gap-1.5">
          <ShieldCheck className="w-4 h-4 text-emerald-400" /> Active Security Profile
        </div>
        <div className="p-3.5 rounded-xl bg-slate-800/60 border border-slate-700/60 shadow-inner">
          <div className="font-semibold text-slate-100 text-sm">{currentSession.name}</div>
          <div className="text-xs text-slate-400 mt-0.5">{currentSession.dept}</div>
          <div className="mt-3 flex items-center justify-between">
            <span className="text-xs font-mono px-2.5 py-1 rounded-md bg-slate-950 border border-slate-700 text-slate-300 font-medium">
              role: {currentSession.role}
            </span>
            {sqlRagPermitted ? (
              <span className="text-[10px] font-bold px-2 py-0.5 rounded bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 flex items-center gap-1">
                <Database className="w-3 h-3" /> SQL RAG
              </span>
            ) : (
              <span className="text-[10px] font-bold px-2 py-0.5 rounded bg-slate-800 text-slate-400 border border-slate-700 flex items-center gap-1">
                <FileText className="w-3 h-3" /> Doc RAG Only
              </span>
            )}
          </div>
        </div>
      </div>

      {/* Accessible Document Collections */}
      <div className="p-5 border-b border-slate-800/80">
        <div className="text-xs font-semibold tracking-wider text-slate-400 uppercase mb-3 flex items-center justify-between">
          <span>Vector Store Permissions</span>
          <span className="text-[10px] text-emerald-400 font-mono">Qdrant Filter Active</span>
        </div>
        <div className="space-y-2">
          {['general', 'clinical', 'nursing', 'billing', 'equipment'].map((col) => {
            const isAccessible = accessibleCollections.includes(col);
            return (
              <div 
                key={col}
                className={`flex items-center justify-between px-3 py-2 rounded-lg text-xs transition-all ${
                  isAccessible 
                    ? 'bg-emerald-950/20 border border-emerald-800/30 text-emerald-200' 
                    : 'bg-slate-950/30 border border-slate-800/40 text-slate-500 opacity-60'
                }`}
              >
                <div className="flex items-center gap-2">
                  <FileText className={`w-3.5 h-3.5 ${isAccessible ? 'text-emerald-400' : 'text-slate-600'}`} />
                  <span className="capitalize font-mono">{col}</span>
                </div>
                {isAccessible ? (
                  <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400" />
                ) : (
                  <Lock className="w-3.5 h-3.5 text-slate-600" />
                )}
              </div>
            );
          })}
        </div>
      </div>

      {/* Quick Role Switcher */}
      <div className="p-5 flex-1">
        <div className="text-xs font-semibold tracking-wider text-slate-400 uppercase mb-3">
          Switch Demo Role
        </div>
        <div className="space-y-2">
          {DEMO_ROLES.map((r) => {
            const isSelected = currentSession.role === r.role;
            return (
              <button
                key={r.role}
                onClick={() => onSwitchRole(r.role)}
                className={`w-full text-left p-3 rounded-xl border transition-all flex items-center justify-between group ${
                  isSelected 
                    ? 'bg-blue-600/10 border-blue-500/50 shadow-lg shadow-blue-900/10' 
                    : 'bg-slate-800/30 border-slate-700/40 hover:bg-slate-800/60 hover:border-slate-600'
                }`}
              >
                <div className="flex items-center gap-3">
                  <div className="p-2 rounded-lg bg-slate-900/80 border border-slate-700/60">
                    {r.icon}
                  </div>
                  <div>
                    <div className="text-xs font-semibold text-slate-200">{r.label}</div>
                    <div className="text-[11px] text-slate-400">{r.username}</div>
                  </div>
                </div>
                {isSelected && (
                  <span className="w-2 h-2 rounded-full bg-blue-400 shadow-sm shadow-blue-400 animate-pulse" />
                )}
              </button>
            );
          })}
        </div>
      </div>
    </aside>
  );
};
