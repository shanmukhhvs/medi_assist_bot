import { Role, UserSession, AccessibleCollectionsResponse } from './types';

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

export async function loginUser(username: string, password: string): Promise<UserSession> {
  const res = await fetch(`${API_BASE_URL}/login`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ username, password }),
  });

  if (!res.ok) {
    const errData = await res.json().catch(() => ({}));
    throw new Error(errData.detail || 'Login failed');
  }

  const data = await res.json();
  return {
    username,
    role: data.role as Role,
    name: data.name,
    dept: data.dept,
    token: data.access_token,
  };
}

export async function fetchAccessibleCollections(role: Role, token: string): Promise<AccessibleCollectionsResponse> {
  const res = await fetch(`${API_BASE_URL}/collections/${role}`, {
    headers: { Authorization: `Bearer ${token}` },
  });
  if (!res.ok) {
    throw new Error('Failed to fetch accessible collections');
  }
  return res.json();
}

export async function sendChatMessage(question: string, role: Role, token?: string) {
  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
  };
  if (token) {
    headers['Authorization'] = `Bearer ${token}`;
  }

  const res = await fetch(`${API_BASE_URL}/chat`, {
    method: 'POST',
    headers,
    body: JSON.stringify({ question, role }),
  });

  if (!res.ok) {
    const errData = await res.json().catch(() => ({}));
    throw new Error(errData.detail || 'Chat request failed');
  }

  return res.json();
}
