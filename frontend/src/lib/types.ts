export type Role = 'doctor' | 'nurse' | 'billing_executive' | 'technician' | 'admin';

export interface UserSession {
  username: string;
  role: Role;
  name: string;
  dept: string;
  token: string;
}

export interface SourceCitation {
  source_document: string;
  section_title: string;
  collection: string;
}

export interface ChatMessage {
  id: string;
  sender: 'user' | 'bot';
  text: string;
  timestamp: string;
  role?: Role;
  retrieval_type?: 'hybrid_rag' | 'sql_rag';
  blocked?: boolean;
  sources?: SourceCitation[];
  executed_sql?: string;
  isError?: boolean;
}

export interface AccessibleCollectionsResponse {
  role: Role;
  collections: string[];
  sql_rag_permitted: boolean;
}
