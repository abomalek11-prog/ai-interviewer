import { API_BASE_URL, apiClient } from "./client";
import { tokenStorage } from "./tokenStorage";
import type {
  AnalyticsSummary,
  AIModelProfile,
  AuthResponse,
  Candidate,
  CandidateStatus,
  CandidateWithJob,
  InterviewSession,
  Job,
  JobStatus,
  JobWithStats,
  RoleCategory,
  Seniority,
  SessionMode,
  SessionSummary,
  User,
} from "@/types/api";

export const aiApi = {
  listModelProfiles: () => apiClient.get<AIModelProfile[]>("/ai/model-profiles").then((r) => r.data),
  transcribe: (audioBlob: Blob) => {
    const form = new FormData();
    form.append("audio", audioBlob, "answer.webm");
    return apiClient
      .post<{ text: string }>("/ai/transcribe", form, { headers: { "Content-Type": "multipart/form-data" } })
      .then((r) => r.data);
  },
};

export type OAuthProvider = "google" | "github" | "x" | "apple";

export const authApi = {
  register: (payload: { email: string; password: string; full_name: string }) =>
    apiClient.post<AuthResponse>("/auth/register", payload).then((r) => r.data),
  login: (payload: { email: string; password: string }) =>
    apiClient.post<AuthResponse>("/auth/login", payload).then((r) => r.data),
  me: () => apiClient.get<User>("/auth/me").then((r) => r.data),
  forgotPassword: (email: string) => apiClient.post<{ message: string }>("/auth/forgot-password", { email }).then((r) => r.data),
  verifyOtp: (email: string, code: string) =>
    apiClient.post<{ message: string }>("/auth/verify-otp", { email, code }).then((r) => r.data),
  resetPassword: (payload: { email: string; code: string; new_password: string }) =>
    apiClient.post<{ message: string }>("/auth/reset-password", payload).then((r) => r.data),
  oauthProviders: () => apiClient.get<Record<OAuthProvider, boolean>>("/auth/oauth/providers").then((r) => r.data),
  oauthLoginUrl: (provider: OAuthProvider) => `${API_BASE_URL}/auth/oauth/${provider}/login`,
};

export const usersApi = {
  updateProfile: (payload: Partial<Pick<User, "full_name" | "title" | "bio" | "profile_picture_url">>) =>
    apiClient.patch<User>("/users/me", payload).then((r) => r.data),
  changePassword: (payload: { current_password: string; new_password: string }) =>
    apiClient.patch<{ message: string }>("/users/me/password", payload).then((r) => r.data),
  uploadAvatar: (file: File) => {
    const form = new FormData();
    form.append("file", file);
    return apiClient.post<User>("/users/me/avatar", form, { headers: { "Content-Type": "multipart/form-data" } }).then((r) => r.data);
  },
};

export const jobsApi = {
  list: () => apiClient.get<JobWithStats[]>("/jobs").then((r) => r.data),
  get: (id: string) => apiClient.get<Job>(`/jobs/${id}`).then((r) => r.data),
  create: (payload: {
    title: string;
    role_category: RoleCategory;
    seniority: Seniority;
    description?: string;
    duration_minutes?: number;
    task_count?: number;
    ai_model_profile_id?: string | null;
  }) => apiClient.post<Job>("/jobs", payload).then((r) => r.data),
  update: (id: string, payload: Partial<{ title: string; status: JobStatus; description: string; ai_model_profile_id: string | null }>) =>
    apiClient.patch<Job>(`/jobs/${id}`, payload).then((r) => r.data),
  remove: (id: string) => apiClient.delete(`/jobs/${id}`),
};

export const candidatesApi = {
  list: (jobId?: string) =>
    apiClient.get<CandidateWithJob[]>("/candidates", { params: jobId ? { job_id: jobId } : undefined }).then((r) => r.data),
  get: (id: string) => apiClient.get<Candidate>(`/candidates/${id}`).then((r) => r.data),
  create: (payload: { job_id: string; full_name: string; email: string; resume_url?: string }) =>
    apiClient.post<Candidate>("/candidates", payload).then((r) => r.data),
  update: (id: string, payload: Partial<{ status: CandidateStatus; resume_url: string }>) =>
    apiClient.patch<Candidate>(`/candidates/${id}`, payload).then((r) => r.data),
};

export const interviewsApi = {
  list: (limit = 50, candidateId?: string) =>
    apiClient
      .get<SessionSummary[]>("/interviews", { params: candidateId ? { limit, candidate_id: candidateId } : { limit } })
      .then((r) => r.data),
  get: (id: string) => apiClient.get<InterviewSession>(`/interviews/${id}`).then((r) => r.data),
  create: (payload: { job_id: string; candidate_id: string; ai_model_profile_id?: string | null; mode?: SessionMode }) =>
    apiClient.post<InterviewSession>("/interviews", payload).then((r) => r.data),
  submitAnswer: (sessionId: string, payload: { question_id: string; transcript: string; video_url?: string }) =>
    apiClient.post<InterviewSession>(`/interviews/${sessionId}/answers`, payload).then((r) => r.data),
  liveWsUrl: (sessionId: string) => {
    const token = tokenStorage.getAccessToken() ?? "";
    const wsBase = API_BASE_URL.replace(/^http/, "ws");
    return `${wsBase}/interviews/${sessionId}/live?token=${encodeURIComponent(token)}`;
  },
};

export const analyticsApi = {
  summary: () => apiClient.get<AnalyticsSummary>("/analytics/summary").then((r) => r.data),
};
