import { LineChart, Send } from "lucide-react";
import { useNavigate } from "react-router-dom";

import { interviewsApi, jobsApi } from "@/api/endpoints";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { useAsync } from "@/hooks/useAsync";

const statusBadge: Record<string, "success" | "warning" | "neutral"> = {
  completed: "success",
  in_progress: "warning",
  pending: "neutral",
  abandoned: "neutral",
};

export function InterviewsPage() {
  const navigate = useNavigate();
  const jobs = useAsync(() => jobsApi.list(), []);
  const sessions = useAsync(() => interviewsApi.list(100), []);

  return (
    <>
      <section className="mb-5 flex flex-wrap items-start justify-between gap-4">
        <div>
          <h1 className="text-4xl leading-tight font-bold">Interviews</h1>
          <p className="mt-1.5 max-w-2xl text-base text-foreground/70">
            Manage AI-driven jobs and review every candidate interview session.
          </p>
        </div>
        <Button onClick={() => navigate("/interviews/new")}>
          <Send size={18} />
          <span>New Interview</span>
        </Button>
      </section>

      <Card className="overflow-hidden">
        <div className="flex min-h-16 items-center border-b border-border px-6">
          <CardTitle>Jobs</CardTitle>
        </div>
        {jobs.isLoading && <Skeleton className="m-4 h-16" />}
        {!jobs.isLoading && jobs.data?.length === 0 && (
          <p className="p-6 text-sm text-muted-foreground">No jobs yet. Create your first AI job to begin.</p>
        )}
        {jobs.data?.map((job) => (
          <div key={job.id} className="grid grid-cols-[minmax(0,1fr)_auto_auto_auto] items-center gap-4 border-t border-border px-6 py-4">
            <div>
              <strong className="block">{job.title}</strong>
              <p className="mt-0.5 text-[13px] text-foreground/70">
                {job.role_category} - {job.seniority} - {job.duration_minutes} mins - {job.task_count} tasks
              </p>
            </div>
            <Badge variant={job.status === "active" ? "success" : job.status === "paused" ? "warning" : "neutral"}>
              {job.status}
            </Badge>
            <span className="font-mono text-[13px] text-foreground/70">{job.candidate_count} candidates</span>
            <Button size="sm" variant="outline" onClick={() => navigate(`/interviews/new?job=${job.id}`)}>
              Add candidate
            </Button>
          </div>
        ))}
      </Card>

      <Card className="mt-4 overflow-hidden">
        <div className="flex min-h-16 items-center gap-2 border-b border-border px-6">
          <LineChart size={18} />
          <CardTitle>All Sessions</CardTitle>
        </div>
        {sessions.isLoading && <Skeleton className="m-4 h-16" />}
        {!sessions.isLoading && sessions.data?.length === 0 && (
          <p className="p-6 text-sm text-muted-foreground">No interview sessions yet.</p>
        )}
        {sessions.data?.map((session) => (
          <button
            key={session.id}
            onClick={() => navigate(`/interviews/session/${session.id}`)}
            className="grid w-full grid-cols-[minmax(0,1fr)_auto_auto] items-center gap-4 border-t border-border px-6 py-4 text-left hover:bg-muted/40"
          >
            <div>
              <strong className="block">{session.candidate_name}</strong>
              <p className="mt-0.5 text-[13px] text-foreground/70">{session.job_title}</p>
            </div>
            <span className="font-mono text-sm font-extrabold">{session.overall_score ?? "-"}</span>
            <Badge variant={statusBadge[session.status]}>{session.status.replace("_", " ")}</Badge>
          </button>
        ))}
      </Card>
    </>
  );
}
