import { CalendarDays, CheckCircle2, LineChart, Settings, ShieldCheck, Sparkles, UsersRound } from "lucide-react";
import { useNavigate } from "react-router-dom";

import { analyticsApi, interviewsApi, jobsApi } from "@/api/endpoints";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { useAsync } from "@/hooks/useAsync";

const statusBadge: Record<string, "success" | "warning" | "neutral"> = {
  completed: "success",
  in_progress: "warning",
  pending: "neutral",
  abandoned: "neutral",
};

export function DashboardPage() {
  const navigate = useNavigate();
  const analytics = useAsync(() => analyticsApi.summary(), []);
  const jobs = useAsync(() => jobsApi.list(), []);
  const sessions = useAsync(() => interviewsApi.list(6), []);

  const maxTrend = Math.max(1, ...(analytics.data?.trend_30d.map((p) => p.completed) ?? [1]));

  return (
    <>
      <section className="mb-5 flex flex-wrap items-start justify-between gap-4">
        <div>
          <h1 className="text-4xl leading-tight font-bold">System Overview</h1>
          <p className="mt-1.5 max-w-2xl text-base text-foreground/70">
            Track interviews, jobs, candidates, and AI assessment quality from one workspace.
          </p>
        </div>
        <Button onClick={() => navigate("/interviews/new")}>
          <Sparkles size={20} />
          <span>New AI Job</span>
        </Button>
      </section>

      <section className="grid grid-cols-1 gap-4 sm:grid-cols-3">
        <Card className="p-5">
          <div className="mb-4.5 flex items-center gap-3.5">
            <div className="grid size-11.5 place-items-center rounded-[10px] bg-[#dce3ff]">
              <UsersRound size={23} />
            </div>
            <span className="font-mono text-xs text-success">
              {analytics.data ? `${analytics.data.total_interviews} total` : "..."}
            </span>
          </div>
          <p className="text-[13px] tracking-[2px] text-foreground/60">TOTAL INTERVIEWS</p>
          <strong className="mt-1.5 block text-4xl">{analytics.data?.total_interviews ?? <Skeleton className="h-9 w-16" />}</strong>
        </Card>

        <Card className="p-5">
          <div className="mb-4.5 flex items-center gap-3.5">
            <div className="grid size-11.5 place-items-center rounded-[10px] bg-[#4cdda0]">
              <ShieldCheck size={23} />
            </div>
          </div>
          <p className="text-[13px] tracking-[2px] text-foreground/60">SUCCESS RATE</p>
          <strong className="mt-1.5 block text-4xl">
            {analytics.data ? `${analytics.data.success_rate}%` : <Skeleton className="h-9 w-16" />}
          </strong>
        </Card>

        <Card className="bg-secondary p-5 text-white">
          <div className="mb-4.5 grid size-12 place-items-center rounded-[10px] bg-white/10">
            <LineChart size={24} />
          </div>
          <p className="text-[13px] tracking-[2px] text-white/60">AVG AI SCORE</p>
          <strong className="mt-1.5 block text-4xl">
            {analytics.data ? analytics.data.avg_ai_score : <Skeleton className="h-9 w-16 bg-white/20" />}
            <span className="ml-1 text-[15px] text-white/60">/100</span>
          </strong>
        </Card>
      </section>

      <section className="mt-4 grid grid-cols-1 gap-4 lg:grid-cols-[minmax(0,2fr)_minmax(280px,1fr)]">
        <Card className="min-h-75 p-5.5">
          <CardHeader className="flex-row items-center justify-between p-0">
            <CardTitle>Interview Completion Trend (30 days)</CardTitle>
          </CardHeader>
          <div className="mt-4 flex h-58 items-end gap-1">
            {analytics.isLoading && <Skeleton className="h-full w-full" />}
            {!analytics.isLoading && (analytics.data?.trend_30d.length ?? 0) === 0 && (
              <p className="self-center text-sm text-muted-foreground">No completed interviews yet.</p>
            )}
            {analytics.data?.trend_30d.map((point) => (
              <div key={point.date} className="flex flex-1 flex-col items-center gap-1" title={`${point.date}: ${point.completed}`}>
                <div
                  className="w-full rounded-t bg-primary/80"
                  style={{ height: `${Math.max(6, (point.completed / maxTrend) * 100)}%` }}
                />
              </div>
            ))}
          </div>
        </Card>

        <Card className="min-h-75 p-5.5">
          <CardTitle>Job Difficulty</CardTitle>
          <div className="mt-5 grid place-items-center">
            <div className="grid size-40 place-items-center rounded-full bg-[conic-gradient(theme(colors.secondary)_0_65%,theme(colors.primary)_65%_90%,theme(colors.destructive)_90%_100%)]">
              <div className="grid size-28 place-items-center rounded-full bg-white text-center">
                <strong className="text-xl font-bold">{analytics.data?.total_jobs ?? 0}</strong>
                <span className="mt-0.5 font-mono text-xs tracking-[2px]">JOBS</span>
              </div>
            </div>
          </div>
          <div className="mt-5 grid grid-cols-2 gap-3 text-sm">
            {(analytics.data?.difficulty_breakdown ?? []).map((item) => (
              <div key={item.seniority} className="flex items-start gap-2">
                <span className="mt-1.5 size-2.5 rounded-full bg-primary" />
                <p>
                  {item.seniority}
                  <br />({item.percentage}%)
                </p>
              </div>
            ))}
          </div>
        </Card>
      </section>

      <section className="mt-4 grid grid-cols-1 gap-4 lg:grid-cols-[minmax(0,2fr)_minmax(280px,1fr)]">
        <Card className="p-4.5">
          <div className="flex items-center justify-between">
            <div>
              <CardTitle>Recent Interviews</CardTitle>
              <p className="mt-1 text-[13px] text-muted-foreground">{sessions.data?.length ?? 0} most recent</p>
            </div>
            <CalendarDays size={20} />
          </div>
          <div className="mt-3.5 grid gap-2.5">
            {sessions.isLoading && <Skeleton className="h-16 w-full" />}
            {!sessions.isLoading && sessions.data?.length === 0 && (
              <p className="text-sm text-muted-foreground">No interviews yet. Start one from a job.</p>
            )}
            {sessions.data?.map((session) => (
              <button
                key={session.id}
                onClick={() => navigate(`/interviews/session/${session.id}`)}
                className="grid grid-cols-[minmax(0,1fr)_auto_auto] items-center gap-2.5 rounded-lg border border-border bg-[#fbfcfd] p-2.5 text-left"
              >
                <div>
                  <strong className="block text-sm">{session.candidate_name}</strong>
                  <p className="mt-0.5 text-[13px] text-muted-foreground">{session.job_title}</p>
                </div>
                <span className="font-mono text-sm font-extrabold">{session.overall_score ?? "-"}</span>
                <Badge variant={statusBadge[session.status]}>{session.status.replace("_", " ")}</Badge>
              </button>
            ))}
          </div>
        </Card>

        <Card className="p-4.5">
          <div className="flex items-center justify-between">
            <div>
              <CardTitle>Live Activity</CardTitle>
              <p className="mt-1 text-[13px] text-muted-foreground">Latest system events</p>
            </div>
            <Settings size={20} />
          </div>
          <div className="mt-3.5 grid gap-2.5">
            {sessions.data?.slice(0, 5).map((session) => (
              <div key={session.id} className="grid grid-cols-[22px_minmax(0,1fr)] items-center gap-2 text-sm">
                <CheckCircle2 size={18} className="text-primary" />
                <span>
                  {session.candidate_name} - {session.job_title} ({session.status.replace("_", " ")})
                </span>
              </div>
            ))}
          </div>
        </Card>
      </section>

      <section className="mt-4 overflow-hidden rounded-xl border border-border">
        <div className="flex min-h-16.5 items-center justify-between border-b border-border px-6">
          <CardTitle>Recent AI Jobs</CardTitle>
          <Button variant="link" onClick={() => navigate("/interviews")}>
            View All Jobs
          </Button>
        </div>
        <div className="grid grid-cols-[minmax(300px,1.35fr)_minmax(110px,0.55fr)_minmax(150px,0.65fr)_minmax(140px,0.55fr)] items-center bg-muted px-6 py-2.5 text-xs font-extrabold tracking-[2px] text-foreground/70">
          <span>JOB TITLE</span>
          <span>STATUS</span>
          <span>DIFFICULTY</span>
          <span>CANDIDATES</span>
        </div>
        {jobs.isLoading && <Skeleton className="m-4 h-16" />}
        {!jobs.isLoading && jobs.data?.length === 0 && (
          <p className="p-6 text-sm text-muted-foreground">No jobs yet. Create one to get started.</p>
        )}
        {jobs.data?.slice(0, 5).map((job) => (
          <div
            key={job.id}
            className="grid min-h-18 grid-cols-[minmax(300px,1.35fr)_minmax(110px,0.55fr)_minmax(150px,0.65fr)_minmax(140px,0.55fr)] items-center border-t border-border px-6"
          >
            <div className="flex items-center gap-3">
              <span className="grid size-9.5 place-items-center rounded-lg bg-[#c7d0ea] text-sm font-extrabold">
                {job.title.slice(0, 2).toUpperCase()}
              </span>
              <div>
                <strong className="block text-[15px]">{job.title}</strong>
                <p className="mt-0.5 text-[13px] text-foreground/70">
                  {job.role_category} - {job.seniority}
                </p>
              </div>
            </div>
            <Badge variant={job.status === "active" ? "success" : job.status === "paused" ? "warning" : "neutral"}>
              {job.status}
            </Badge>
            <Badge variant="neutral">{job.seniority}</Badge>
            <span className="justify-self-end font-mono text-[13px]">{job.candidate_count} Candidates</span>
          </div>
        ))}
      </section>
    </>
  );
}
