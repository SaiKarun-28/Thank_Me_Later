export type StorageKind = 'session' | 'local';
export type RemotePreference = 'remote' | 'hybrid' | 'onsite' | 'any';
export type ExperienceLevel = 'intern' | 'fresher' | 'junior' | 'mid' | 'senior' | 'lead';

export interface TargetRole { role: string; confidence: number; }
export interface ParsedProfile {
  name: string;
  contact: Record<string, string | null | undefined>;
  skills: string[];
  years_experience: number;
  target_roles: TargetRole[];
  past_titles: string[];
  domains: string[];
  experience: unknown[];
  projects: unknown[];
  education: unknown[];
  certifications: string[];
  raw_text: string;
}
export interface ConfirmedProfile {
  skills: string[];
  target_roles: TargetRole[];
  location: string;
  remote_preference: RemotePreference;
  experience_level: ExperienceLevel;
  years_experience: number;
}
export interface Provider { id: string; name: string; default_model: string; available_models: string[]; requires_key: boolean; allows_custom_url: boolean; default_base_url?: string | null; }
export interface SourceField { key: string; label: string; type: 'text' | 'password' | 'select' | 'list'; required: boolean; default: string | string[] | null; options?: string[] | null; description?: string | null; }
export interface SourceMeta { id: string; name: string; is_keyless: boolean; fields: SourceField[]; attribution?: string | null; terms_url?: string | null; }
export interface Settings { provider: string; model: string; apiKey: string; baseUrl: string; sources: Record<string, string | boolean>; storage: StorageKind; }
export interface Progress { stage: string; percent: number; message: string; }
export interface SourceStatus { source_id: string; status: 'pending' | 'loading' | 'success' | 'error'; count: number; message?: string | null; }
export interface RankedJob {
  id: string; title: string; company: string; location: string; remote: boolean; description: string; apply_url: string;
  heuristic_score: number; llm_score: number | null; final_score: number; match_reason: string; required_skills: string[]; matched_skills: string[]; missing_skills: string[]; posted_date: string | null; source: string; salary: string | null;
}
