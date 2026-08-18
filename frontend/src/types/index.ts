// ── Auth ─────────────────────────────────────────────────────────────
export interface User {
  id: number;
  email: string;
  name: string;
  role: 'owner' | 'admin' | 'recruiter' | 'viewer';
  org_id: number;
  org_name?: string;
}

export interface TokenResponse {
  access_token: string;
  token_type: string;
}

// ── Job ──────────────────────────────────────────────────────────────
export interface Job {
  id: number;
  org_id: number;
  recruiter_id: number;
  title: string;
  company?: string;
  description: string;
  required_skills: string[];
  nice_to_have: string[];
  min_experience: number;
  max_experience?: number;
  education_req?: string;
  location_req?: string;
  hr_email?: string;
  salary_min?: number;
  salary_max?: number;
  is_active: boolean;
  apply_url: string;
  score_strong_match: number;
  score_potential_match: number;
  score_weak_match: number;
  candidate_count: number;
  created_at: string;
  updated_at?: string;
}

export interface JobCreate {
  title: string;
  company?: string;
  description: string;
  required_skills: string[];
  nice_to_have: string[];
  min_experience: number;
  max_experience?: number;
  education_req?: string;
  location_req?: string;
  hr_email?: string;
  salary_min?: number;
  salary_max?: number;
  score_strong_match?: number;
  score_potential_match?: number;
  score_weak_match?: number;
}

export interface KnockoutRule {
  id: number;
  job_id: number;
  rule_type: string;
  field?: string;
  operator?: string;
  value?: string;
  action: string;
  description: string;
  is_active: boolean;
  is_mandatory: boolean;
}

// ── Candidate ────────────────────────────────────────────────────────
export type CandidateStatus =
  | 'Queued' | 'Processing' | 'Error' | 'Duplicate' | 'Knockout Failed'
  | 'Under Review' | 'Screening' | 'Phone Interview' | 'Technical'
  | 'Final Interview' | 'Shortlisted' | 'Offer Sent' | 'Hired'
  | 'Rejected' | 'Withdrew' | 'Ghosted' | 'Interview' | 'Approved';

export type CandidateCategory = 'STRONG_MATCH' | 'POTENTIAL_MATCH' | 'WEAK_MATCH' | 'NEEDS_REVIEW' | 'KNOCKOUT_FAILED';
export type RecruiterDecision = 'NEEDS_REVIEW' | 'APPROVED' | 'REJECTED';
export type Recommendation = 'Strong Hire' | 'Hire' | 'Consider' | 'Reject';

export interface Education {
  degree: string;
  field: string;
  institution: string;
  year?: string;
  gpa?: number;
}

export interface Certification {
  name: string;
  issuer?: string;
  year?: number;
}

export interface Position {
  title: string;
  company: string;
  start?: string;
  end?: string;
  duration_months?: number;
}

export interface Language {
  language: string;
  level: string;
}

export interface Project {
  name: string;
  description?: string;
  technologies?: string[];
  url?: string;
}

export interface PipelineHistoryEntry {
  stage: string;
  entered_at: string;
  exited_at?: string;
  days?: number;
  notes?: string;
  moved_by?: string;
}

export interface ChatMessage {
  role: 'user' | 'assistant';
  content: string;
  created_at: string;
}

export interface CandidateAnalysis {
  overall_score: number;
  skill_match: number;
  experience_match: number;
  education_match: number;
  seniority_match: number;
  location_match: number;
  ats_score: number;
  ai_confidence: number;
  matched_skills: string[];
  missing_skills: string[];
  matched_requirements: string[];
  missing_requirements: string[];
  score_breakdown: Record<string, { score: number; weight: number; weighted: number }>;
  recommendation: Recommendation;
  recommendation_reason: string;
  ai_summary: string;
  strengths: string[];
  weaknesses: string[];
  skill_gap_analysis: string;
  ats_issues: string[];
  ats_suggestions: string[];
  category: CandidateCategory;
  rank?: number;
  percentile?: number;
  llm_provider?: string;
  processing_time_ms?: number;
}

export interface Candidate {
  id: number;
  org_id: number;
  recruiter_id?: number;
  job_id?: number;
  batch_id?: number;
  full_name: string;
  email?: string;
  phone?: string;
  whatsapp_phone?: string;
  location?: string;
  nationality?: string;
  linkedin?: string;
  github?: string;
  portfolio?: string;
  current_position?: string;
  years_experience: number;
  previous_positions: Position[];
  companies: string[];
  education: Education[];
  certifications: Certification[];
  courses: string[];
  technical_skills: Record<string, string[]>;
  soft_skills: string[];
  languages: Language[];
  projects: Project[];
  achievements: string[];
  awards: string[];
  match_score: number;
  ats_score: number;
  skill_match: number;
  experience_match: number;
  education_match: number;
  seniority_match: number;
  location_match: number;
  keyword_match: number;
  salary_match: number;
  ai_confidence: number;
  recommendation?: Recommendation;
  recommendation_reason?: string;
  ai_summary?: string;
  strengths: string[];
  weaknesses: string[];
  missing_skills: string[];
  missing_certs: string[];
  skill_gap_analysis?: string;
  ats_issues: string[];
  ats_suggestions: string[];
  rank?: number;
  category: CandidateCategory;
  status: CandidateStatus;
  pipeline_stage?: string;
  pipeline_history: PipelineHistoryEntry[];
  recruiter_decision: RecruiterDecision;
  decision_notes?: string;
  decided_at?: string;
  salary_expectation?: number;
  salary_currency?: string;
  notice_period_days?: number;
  availability_date?: string;
  remote_preference?: string;
  salary_expectation_match?: string;
  offer_amount?: number;
  offer_currency?: string;
  offer_sent_at?: string;
  offer_deadline?: string;
  offer_accepted?: boolean;
  applied_at: string;
  shortlisted_at?: string;
  hired_at?: string;
  rejected_at?: string;
  interview_scheduled?: string;
  interview_type?: string;
  interview_link?: string;
  interview_location?: string;
  interview_duration_mins?: number;
  flagged: boolean;
  flag_reason?: string;
  is_knocked_out: boolean;
  knockout_flags: string[];
  source: string;
  file_name?: string;
  duplicate_of?: number;
  processing_attempts: number;
  last_error?: string;
  chat_history: ChatMessage[];
  whatsapp_history: { type: string; body: string; status: string; created_at: string }[];
  analysis?: CandidateAnalysis;
  created_at: string;
}

// ── Paginated ────────────────────────────────────────────────────────
export interface Paginated<T> {
  total: number;
  page: number;
  page_size: number;
  pages: number;
  items: T[];
}

// ── Dashboard ────────────────────────────────────────────────────────
export interface DashboardStats {
  total_candidates: number;
  today: number;
  queued: number;
  processing: number;
  pending: number;
  shortlisted: number;
  interview: number;
  hired: number;
  rejected: number;
  duplicates: number;
  knocked_out: number;
  errors: number;
  avg_match_score: number;
  active_jobs: number;
  active_batches: number;
  category_breakdown: Record<string, number>;
  decision_breakdown: Record<string, number>;
  source_breakdown: Record<string, number>;
  daily_trend: { date: string; count: number }[];
  top_skills: { skill: string; count: number }[];
  hiring_funnel: Record<string, number>;
}

export interface PipelineAnalytics {
  total_candidates: number;
  funnel: Record<string, { count: number; pct_of_total: number }>;
  avg_stage_days: Record<string, number>;
  avg_time_to_hire_days?: number;
  source_quality: Record<string, { total: number; shortlisted: number; hired: number; shortlist_rate: number; hire_rate: number }>;
  offer_stats: { sent: number; accepted: number; acceptance_rate_pct: number };
  salary_match_distribution: Record<string, number>;
}

// ── Batch ────────────────────────────────────────────────────────────
export interface BatchJob {
  batch_id: number;
  status: string;
  total: number;
  completed: number;
  failed: number;
  processing: number;
  progress_pct: number;
  status_breakdown: Record<string, number>;
  error_log: { file?: string; error: string }[];
  started_at?: string;
  completed_at?: string;
  created_at: string;
  track_url?: string;
}

// ── Timeline ─────────────────────────────────────────────────────────
export interface TimelineEvent {
  type: string;
  label: string;
  at?: string;
  by?: string;
  notes?: string;
}

// ── Webhook ──────────────────────────────────────────────────────────
export interface WebhookEndpoint {
  id: number;
  url: string;
  events: string[];
  is_active: boolean;
  description?: string;
  created_at: string;
}

export interface WebhookDelivery {
  id: number;
  event: string;
  status_code?: number;
  success: boolean;
  attempt: number;
  error?: string;
  created_at: string;
}

// ── Team User ────────────────────────────────────────────────────────
export interface TeamUser {
  id: number;
  name: string;
  email: string;
  role: string;
  is_active: boolean;
  org_id: number;
  created_at: string;
}

// ── Time to Hire ─────────────────────────────────────────────────────
export interface TimeToHireReport {
  period_days: number;
  total_hired: number;
  overall_avg_days?: number;
  by_job: {
    job_id: number | string;
    job_title: string;
    hired_count: number;
    avg_days: number;
    min_days: number;
    max_days: number;
  }[];
}
