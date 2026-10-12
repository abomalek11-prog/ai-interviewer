export type RoleCategory = "Frontend" | "Backend" | "Fullstack" | "Mobile" | "DevOps";
export type Seniority = "Junior" | "Mid-level" | "Senior";
export type JobStatus = "draft" | "active" | "paused" | "closed";
export type CandidateStatus = "new" | "interviewing" | "shortlisted" | "rejected" | "hired";
export type SessionStatus = "pending" | "in_progress" | "completed" | "abandoned";
export type SessionMode = "structured" | "live";
export type MessageRole = "ai" | "candidate";

export interface User {
  id: string;
  email: string;
  full_name: string;
  title: string | null;
  bio: string | null;
  profile_picture_url: string | null;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface AuthResponse {
  access_token: string;
  refresh_token: string;
  token_type: string;
  user: User;
}

export interface Job {
  id: string;
  title: string;
  role_category: RoleCategory;
  seniority: Seniority;
  status: JobStatus;
  description: string | null;
  duration_minutes: number;
  task_count: number;
  ai_model_profile_id: string | null;
  created_at: string;
  updated_at: string;
}

export interface AIModelProfile {
  id: string;
  label: string;
  model: string;
  is_available: boolean;
}

export interface JobWithStats extends Job {
  candidate_count: number;
}

export interface Candidate {
  id: string;
  job_id: string;
  full_name: string;
  email: string;
  resume_url: string | null;
  status: CandidateStatus;
  created_at: string;
  updated_at: string;
}

export interface CandidateWithJob extends Candidate {
  job_title: string;
  latest_score: number | null;
}

export interface Evaluation {
  id: string;
  score: number;
  correctness: number;
  depth: number;
  clarity: number;
  terminology: number;
  feedback: string;
  strengths: string[];
  improvements: string[];
}

export interface Answer {
  id: string;
  question_id: string;
  transcript: string;
  video_url: string | null;
  submitted_at: string;
  evaluation: Evaluation | null;
}

export interface Question {
  id: string;
  order_index: number;
  prompt: string;
  expected_topics: string[];
  time_limit_seconds: number;
  answer: Answer | null;
}

export interface ConversationMessage {
  id: string;
  role: MessageRole;
  content: string;
  created_at: string;
}

export interface QuestionInsight {
  topic: string;
  score: number;
  comment: string;
}

/** Whole-interview assessment of a live conversation (structured interviews score per answer instead). */
export interface SessionEvaluation {
  score: number;
  correctness: number;
  depth: number;
  clarity: number;
  terminology: number;
  feedback: string;
  strengths: string[];
  improvements: string[];
  question_breakdown: QuestionInsight[];
}

export interface InterviewSession {
  id: string;
  job_id: string;
  candidate_id: string;
  status: SessionStatus;
  mode: SessionMode;
  interview_type: string;
  difficulty: string;
  ai_model_profile_id: string | null;
  overall_score: number | null;
  started_at: string | null;
  completed_at: string | null;
  created_at: string;
  questions: Question[];
  conversation_messages: ConversationMessage[];
  evaluation: SessionEvaluation | null;
}

export interface SessionSummary {
  id: string;
  candidate_id: string;
  candidate_name: string;
  job_title: string;
  status: SessionStatus;
  overall_score: number | null;
  started_at: string | null;
  created_at: string;
}

export interface TrendPoint {
  date: string;
  completed: number;
}

export interface DifficultyBreakdownItem {
  seniority: string;
  count: number;
  percentage: number;
}

export interface AnalyticsSummary {
  total_interviews: number;
  completed_interviews: number;
  success_rate: number;
  avg_ai_score: number;
  trend_30d: TrendPoint[];
  difficulty_breakdown: DifficultyBreakdownItem[];
  total_jobs: number;
}
