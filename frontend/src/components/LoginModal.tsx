'use client';

import React, { useState } from 'react';
import { Role, UserSession } from '@/lib/types';
import { loginUser } from '@/lib/api';
import { DEMO_ROLES } from './Sidebar';
import { ShieldCheck, LogIn, Activity, Lock, KeyRound } from 'lucide-react';

interface LoginModalProps {
  isOpen: boolean;
  notice?: string;
  onClose: () => void;
  onLoginSuccess: (session: UserSession) => void;
}

export const LoginModal: React.FC<LoginModalProps> = ({ isOpen, notice, onClose, onLoginSuccess }) => {
  const [selectedRole, setSelectedRole] = useState<Role>('doctor');
  const [password, setPassword] = useState('doctor');
  const [isLoading, setIsLoading] = useState(false);
  const [errorMsg, setErrorMsg] = useState('');

  if (!isOpen) return null;

  const handleRoleSelect = (r: Role) => {
    setSelectedRole(r);
    const demo = DEMO_ROLES.find((d) => d.role === r);
    if (demo) {
      setPassword(demo.username === 'dr.mehta' ? 'doctor' : r);
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsLoading(true);
    setErrorMsg('');

    const demo = DEMO_ROLES.find((d) => d.role === selectedRole);
    const username = demo ? demo.username : 'dr.mehta';

    try {
      const session = await loginUser(username, password);
      onLoginSuccess(session);
      onClose();
    } catch (err: any) {
      setErrorMsg(err.message || 'Login failed');
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 bg-slate-950/80 backdrop-blur-md flex items-center justify-center p-4">
      <div className="bg-slate-900 border border-slate-800 rounded-2xl max-w-lg w-full p-6 shadow-2xl space-y-6 animate-in fade-in zoom-in-95 duration-200">
        {/* Header */}
        <div className="flex items-center gap-3 pb-4 border-b border-slate-800">
          <div className="w-10 h-10 rounded-xl bg-blue-600 flex items-center justify-center shadow-lg shadow-blue-500/20">
            <Activity className="w-6 h-6 text-white" />
          </div>
          <div>
            <h2 className="text-lg font-bold text-slate-100">MediBot RBAC Authentication</h2>
            <p className="text-xs text-slate-400">Select a staff role demo account to authenticate session</p>
          </div>
        </div>

        {notice && (
          <div className="p-3 rounded-lg bg-amber-950/40 border border-amber-800 text-xs text-amber-300">
            {notice}
          </div>
        )}

        {/* Form */}
        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-xs font-semibold text-slate-400 uppercase tracking-wider mb-2">
              Select Staff Role Demo Account
            </label>
            <div className="grid grid-cols-1 gap-2 max-h-56 overflow-y-auto pr-1">
              {DEMO_ROLES.map((r) => {
                const isSelected = selectedRole === r.role;
                return (
                  <div
                    key={r.role}
                    onClick={() => handleRoleSelect(r.role)}
                    className={`p-3 rounded-xl border cursor-pointer transition-all flex items-center justify-between ${
                      isSelected
                        ? 'bg-blue-600/15 border-blue-500 shadow-md'
                        : 'bg-slate-950/40 border-slate-800 hover:bg-slate-800/50'
                    }`}
                  >
                    <div className="flex items-center gap-3">
                      <div className="p-2 rounded-lg bg-slate-900 border border-slate-700">
                        {r.icon}
                      </div>
                      <div>
                        <div className="text-xs font-semibold text-slate-200">{r.label}</div>
                        <div className="text-[11px] text-slate-400">{r.name} ({r.username})</div>
                      </div>
                    </div>
                    {isSelected && <ShieldCheck className="w-4 h-4 text-blue-400" />}
                  </div>
                );
              })}
            </div>
          </div>

          <div>
            <label className="block text-xs font-semibold text-slate-400 uppercase tracking-wider mb-1">
              Password
            </label>
            <div className="relative">
              <KeyRound className="w-4 h-4 text-slate-500 absolute left-3 top-3" />
              <input
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                className="w-full bg-slate-950 border border-slate-700 rounded-xl py-2.5 pl-9 pr-3 text-sm text-slate-100 focus:outline-none focus:border-blue-500"
                required
              />
            </div>
            <p className="text-[11px] text-slate-500 mt-1">Default password matches role name (e.g., doctor, nurse, billing_executive, technician, admin)</p>
          </div>

          {errorMsg && (
            <div className="p-3 rounded-lg bg-red-950/40 border border-red-800 text-xs text-red-300">
              {errorMsg}
            </div>
          )}

          <div className="pt-2 flex items-center justify-end gap-3">
            <button
              type="button"
              onClick={onClose}
              className="px-4 py-2.5 rounded-xl border border-slate-700 text-xs text-slate-300 hover:bg-slate-800 font-medium"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={isLoading}
              className="px-5 py-2.5 rounded-xl bg-blue-600 hover:bg-blue-500 text-white text-xs font-semibold flex items-center gap-2 shadow-lg shadow-blue-600/20"
            >
              <LogIn className="w-4 h-4" />
              <span>{isLoading ? 'Authenticating...' : 'Authenticate & Generate Token'}</span>
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};
