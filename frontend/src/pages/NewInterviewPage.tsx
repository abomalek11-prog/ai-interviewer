import { zodResolver } from "@hookform/resolvers/zod";
import {
  BrainCircuit,
  Code2,
  Database,
  Layers3,
  MessageSquare,
  MonitorSmartphone,
  Send,
  Sparkles,
  TerminalSquare,
  Video,
} from "lucide-react";
import { useEffect, useState } from "react";
import { useForm } from "react-hook-form";
import { useNavigate, useSearchParams } from "react-router-dom";
import { z } from "zod";

import { extractErrorMessage } from "@/api/client";
import { aiApi, candidatesApi, interviewsApi, jobsApi } from "@/api/endpoints";
import { Alert } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { useAsync } from "@/hooks/useAsync";
import { cn } from "@/lib/utils";
import type { Job, RoleCategory, SessionMode, Seniority } from "@/types/api";

const roleCategories: { title: RoleCategory; icon: typeof Code2 }[] = [
  { title: "Frontend", icon: Code2 },
  { title: "Backend", icon: Database },
  { title: "Fullstack", icon: Layers3 },
  { title: "Mobile", icon: MonitorSmartphone },
  { title: "DevOps", icon: TerminalSquare },
];

const seniorities: Seniority[] = ["Junior", "Mid-level", "Senior"];

const jobSchema = z.object({
  title: z.string().min(2, "Enter a job title"),
});

const candidateSchema = z.object({
  full_name: z.string().min(2, "Enter the candidate's name"),
  email: z.string().email("Enter a valid email address"),
});

export function NewInterviewPage() {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const existingJobId = searchParams.get("job");

  const [seniority, setSeniority] = useState<Seniority>("Mid-level");
  const [role, setRole] = useState<RoleCategory>("Frontend");
  const [mode, setMode] = useState<SessionMode>("structured");
  const [job, setJob] = useState<Job | null>(null);
  const [selectedModelProfileId, setSelectedModelProfileId] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [isStarting, setIsStarting] = useState(false);

  const jobs = useAsync(() => jobsApi.list(), []);
  const modelProfiles = useAsync(() => aiApi.listModelProfiles(), []);
  const preselectedJob = existingJobId ? jobs.data?.find((j) => j.id === existingJobId) : null;
  const activeJob = job ?? preselectedJob ?? null;
  const availableProfiles = modelProfiles.data?.filter((profile) => profile.is_available) ?? [];
  const effectiveModelProfileId =
    activeJob?.ai_model_profile_id ?? selectedModelProfileId ?? availableProfiles[0]?.id ?? null;

  useEffect(() => {
    if (!selectedModelProfileId && availableProfiles[0]?.id) {
      setSelectedModelProfileId(availableProfiles[0].id);
    }
  }, [availableProfiles, selectedModelProfileId]);

  const jobForm = useForm<z.infer<typeof jobSchema>>({ resolver: zodResolver(jobSchema) });
  const candidateForm = useForm<z.infer<typeof candidateSchema>>({ resolver: zodResolver(candidateSchema) });

  const createJob = jobForm.handleSubmit(async (values) => {
    setError(null);
    try {
      const created = await jobsApi.create({
        title: values.title,
        role_category: role,
        seniority,
        ai_model_profile_id: effectiveModelProfileId,
      });
      setJob(created);
    } catch (err) {
      setError(extractErrorMessage(err));
    }
  });

  const startInterview = candidateForm.handleSubmit(async (values) => {
    if (!activeJob) return;
    setError(null);
    setIsStarting(true);
    try {
      const candidate = await candidatesApi.create({ job_id: activeJob.id, full_name: values.full_name, email: values.email });
      const session = await interviewsApi.create({
        job_id: activeJob.id,
        candidate_id: candidate.id,
        ai_model_profile_id: effectiveModelProfileId,
        mode,
      });
      navigate(mode === "live" ? `/interviews/live/${session.id}` : `/interviews/session/${session.id}`);
    } catch (err) {
      setError(extractErrorMessage(err, "Could not start the interview"));
      setIsStarting(false);
    }
  });

  return (
    <>
      <section className="mb-5 max-w-3xl">
        <h1 className="text-4xl leading-tight font-bold">
          {activeJob ? "Add a Candidate" : "Choose Your Interview Path"}
        </h1>
        <p className="mt-1.5 text-base text-foreground/70">
          {activeJob
            ? `Add a candidate to start an AI-generated interview for "${activeJob.title}".`
            : "Configure the AI assessment engine by selecting the technical seniority and domain focus required."}
        </p>
      </section>

      {error && <Alert variant="destructive" className="mb-4">{error}</Alert>}

      {!activeJob && (
        <>
          <section className="grid grid-cols-1 gap-7 lg:grid-cols-[minmax(0,2fr)_minmax(280px,0.95fr)]">
            <div>
              <p className="mb-3.5 font-mono text-sm text-foreground/80">SELECT SENIORITY</p>
              <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
                {seniorities.map((title) => (
                  <button
                    key={title}
                    onClick={() => setSeniority(title)}
                    className={cn(
                      "min-h-58 rounded-xl border border-border bg-white p-6 text-left",
                      seniority === title && "border-2 border-secondary shadow-[0_0_0_3px_rgba(17,19,24,0.08)]",
                    )}
                  >
                    <span
                      className={cn(
                        "grid size-12 place-items-center rounded-lg bg-[#e3e7eb]",
                        seniority === title && "bg-secondary text-white",
                      )}
                    >
                      <Sparkles size={24} />
                    </span>
                    <strong className="mt-6 block text-2xl">{title}</strong>
                  </button>
                ))}
              </div>
            </div>

            <aside>
              <p className="mb-3.5 font-mono text-sm text-foreground/80">ROLE CATEGORIES</p>
              <div className="rounded-xl border border-border bg-white p-3.5">
                {roleCategories.map((category) => {
                  const Icon = category.icon;
                  return (
                    <button
                      key={category.title}
                      onClick={() => setRole(category.title)}
                      className={cn(
                        "flex min-h-14 w-full items-center gap-4 rounded-lg px-4.5 text-left text-[17px] font-extrabold",
                        role === category.title && "bg-[#e8eaec]",
                      )}
                    >
                      <Icon size={21} />
                      <span>{category.title}</span>
                    </button>
                  );
                })}
              </div>
            </aside>
          </section>

          <section className="mt-7">
            <p className="mb-3.5 font-mono text-sm text-foreground/80">AI MODEL</p>
            <div className="grid grid-cols-1 gap-3 sm:grid-cols-3">
              {(modelProfiles.data ?? []).map((profile) => (
                <button
                  key={profile.id}
                  type="button"
                  disabled={!profile.is_available}
                  onClick={() => setSelectedModelProfileId(profile.id)}
                  className={cn(
                    "rounded-xl border border-border bg-white p-4 text-left disabled:cursor-not-allowed disabled:opacity-50",
                    effectiveModelProfileId === profile.id && "border-2 border-secondary shadow-[0_0_0_3px_rgba(17,19,24,0.08)]",
                  )}
                >
                  <strong className="block text-base">{profile.label}</strong>
                  <span className="mt-1 block font-mono text-xs text-muted-foreground">{profile.model}</span>
                  {!profile.is_available && <span className="mt-2 block text-xs text-destructive">Missing API key</span>}
                </button>
              ))}
            </div>
          </section>

          <Card className="mt-7 grid grid-cols-1 items-center gap-5 p-7 sm:grid-cols-[auto_minmax(0,1fr)_auto]">
            <BrainCircuit size={30} className="rounded-full bg-[#dce3ff] p-2" />
            <div>
              <p className="font-mono text-xs font-extrabold tracking-[2px] text-primary">PATH OPTIMIZED</p>
              <h2 className="mt-1 text-2xl font-bold">
                {seniority} {role} Specialist
              </h2>
            </div>
            <form onSubmit={createJob} className="flex items-end gap-3">
              <div className="grid gap-1.5">
                <Label htmlFor="title">Job title</Label>
                <Input id="title" placeholder="e.g. Senior Frontend Engineer" {...jobForm.register("title")} />
                {jobForm.formState.errors.title && (
                  <p className="text-xs text-destructive">{jobForm.formState.errors.title.message}</p>
                )}
              </div>
              <Button type="submit" variant="dark" disabled={jobForm.formState.isSubmitting}>
                {jobForm.formState.isSubmitting ? "Creating..." : "Create Job"} <Send size={18} />
              </Button>
            </form>
          </Card>
        </>
      )}

      {activeJob && (
        <Card className="max-w-lg p-7">
          <form onSubmit={startInterview} className="grid gap-4">
            <div className="grid gap-2">
              <Label htmlFor="full_name">Candidate name</Label>
              <Input id="full_name" {...candidateForm.register("full_name")} />
              {candidateForm.formState.errors.full_name && (
                <p className="text-xs text-destructive">{candidateForm.formState.errors.full_name.message}</p>
              )}
            </div>
            <div className="grid gap-2">
              <Label htmlFor="email">Candidate email</Label>
              <Input id="email" type="email" {...candidateForm.register("email")} />
              {candidateForm.formState.errors.email && (
                <p className="text-xs text-destructive">{candidateForm.formState.errors.email.message}</p>
              )}
            </div>
            <div className="grid gap-2">
              <Label>Interview format</Label>
              <div className="grid grid-cols-2 gap-3">
                <button
                  type="button"
                  onClick={() => setMode("structured")}
                  className={cn(
                    "flex items-center gap-2 rounded-lg border border-border p-3 text-left text-sm font-semibold",
                    mode === "structured" && "border-2 border-secondary shadow-[0_0_0_3px_rgba(17,19,24,0.08)]",
                  )}
                >
                  <MessageSquare size={18} /> Structured Q&amp;A
                </button>
                <button
                  type="button"
                  onClick={() => setMode("live")}
                  className={cn(
                    "flex items-center gap-2 rounded-lg border border-border p-3 text-left text-sm font-semibold",
                    mode === "live" && "border-2 border-secondary shadow-[0_0_0_3px_rgba(17,19,24,0.08)]",
                  )}
                >
                  <Video size={18} /> Live AI Conversation
                </button>
              </div>
              <p className="text-xs text-muted-foreground">
                {mode === "live"
                  ? "The AI speaks with the candidate in real time over voice and can see them through the camera."
                  : "The AI generates a fixed question set and scores each typed/spoken answer one at a time."}
              </p>
            </div>
            <Button type="submit" disabled={isStarting}>
              {isStarting ? "Starting..." : mode === "live" ? "Begin Live AI Interview" : "Begin AI Assessment"}{" "}
              <Send size={18} />
            </Button>
          </form>
        </Card>
      )}
    </>
  );
}
