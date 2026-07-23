import { BrainCircuit, CheckCircle2, Star, X } from "lucide-react";
import { useState } from "react";
import { useNavigate, useParams } from "react-router-dom";

import { extractErrorMessage } from "@/api/client";
import { candidatesApi, interviewsApi } from "@/api/endpoints";
import { Alert } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { useAsync } from "@/hooks/useAsync";

export function CandidateReportPage() {
  const { candidateId } = useParams<{ candidateId: string }>();
  const navigate = useNavigate();
  const [actionError, setActionError] = useState<string | null>(null);

  const candidate = useAsync(() => candidatesApi.get(candidateId!), [candidateId]);
  const sessions = useAsync(() => interviewsApi.list(50, candidateId), [candidateId]);
  const latestSessionSummary = sessions.data?.find((s) => s.status === "completed") ?? sessions.data?.[0] ?? null;
  const session = useAsync(
    () => (latestSessionSummary ? interviewsApi.get(latestSessionSummary.id) : Promise.resolve(null)),
    [latestSessionSummary?.id],
  );

  const answers = (session.data?.questions ?? []).filter((q) => q.answer?.evaluation);
  const avg = (key: "correctness" | "depth" | "clarity" | "terminology") =>
    answers.length ? Math.round(answers.reduce((sum, q) => sum + (q.answer!.evaluation![key] ?? 0), 0) / answers.length) : 0;

  const setStatus = async (status: "shortlisted" | "rejected") => {
    if (!candidateId) return;
    setActionError(null);
    try {
      await candidatesApi.update(candidateId, { status });
      candidate.refetch();
    } catch (err) {
      setActionError(extractErrorMessage(err));
    }
  };

  if (candidate.isLoading || sessions.isLoading) return <Skeleton className="h-96 w-full" />;
  if (candidate.error || !candidate.data) return <p className="text-sm text-destructive">{candidate.error ?? "Candidate not found."}</p>;

  return (
    <>
      <section className="mb-6 flex flex-wrap items-end justify-between gap-4">
        <div>
          <p className="text-sm text-muted-foreground">Reports &gt; {candidate.data.full_name}</p>
          <h1 className="mt-2 text-3xl font-bold">Candidate AI Assessment</h1>
        </div>
        <Badge>{candidate.data.status}</Badge>
      </section>

      {actionError && <Alert variant="destructive" className="mb-4">{actionError}</Alert>}

      {!session.data ? (
        <Card className="p-8 text-sm text-muted-foreground">No interview session found for this candidate yet.</Card>
      ) : (
        <>
          <section className="grid grid-cols-1 gap-5 lg:grid-cols-[minmax(260px,0.85fr)_minmax(0,1.75fr)]">
            <Card className="grid justify-items-center gap-4 p-7 text-center">
              <div className="grid size-[170px] place-items-center rounded-full bg-[radial-gradient(circle,#fff_0_58%,transparent_59%),conic-gradient(theme(colors.primary)_0_var(--pct),theme(colors.muted)_var(--pct)_100%)]" style={{ ["--pct" as string]: `${session.data.overall_score ?? 0}%` }}>
                <strong className="text-4xl">{session.data.overall_score ?? "-"}%</strong>
              </div>
              <Badge variant="success">
                <CheckCircle2 size={16} /> {(session.data.overall_score ?? 0) >= 70 ? "Shortlist Recommended" : "Needs Review"}
              </Badge>
              <p className="text-sm text-foreground/70">AI-backed evidence from {answers.length} answered questions.</p>
            </Card>

            <Card className="p-7">
              <CardTitle>Analysis Breakdown</CardTitle>
              <div className="mt-6 grid grid-cols-1 gap-6 sm:grid-cols-2">
                {[
                  { label: "Correctness", value: avg("correctness") },
                  { label: "Depth", value: avg("depth") },
                  { label: "Clarity", value: avg("clarity") },
                  { label: "Terminology", value: avg("terminology") },
                ].map((score) => (
                  <div key={score.label}>
                    <div className="flex justify-between font-mono text-sm">
                      <span>{score.label}</span>
                      <b className="text-primary">{score.value}%</b>
                    </div>
                    <div className="mt-2 h-1.5 rounded-full bg-muted">
                      <div className="h-full rounded-full bg-primary" style={{ width: `${score.value}%` }} />
                    </div>
                  </div>
                ))}
              </div>
            </Card>
          </section>

          <section className="mt-7">
            <h2 className="mb-4 text-lg font-bold">Question-by-Question Insights</h2>
            <div className="grid gap-3">
              {session.data.questions.map((question, index) => (
                <Card key={question.id} className="p-5">
                  <div className="flex items-center gap-3">
                    <span className="font-mono text-xs text-muted-foreground">{String(index + 1).padStart(2, "0")}</span>
                    <p className="flex-1 text-sm font-medium">{question.prompt}</p>
                    {question.answer?.evaluation && <Badge variant="success">Score: {question.answer.evaluation.score}%</Badge>}
                  </div>
                  {question.answer && (
                    <div className="mt-4 grid grid-cols-1 gap-5 border-t border-border pt-4 sm:grid-cols-2">
                      <div>
                        <h3 className="text-xs font-bold tracking-widest text-muted-foreground">CANDIDATE RESPONSE</h3>
                        <p className="mt-2 text-sm leading-relaxed">{question.answer.transcript}</p>
                      </div>
                      {question.answer.evaluation && (
                        <div className="rounded-lg border border-primary/30 bg-primary/5 p-4">
                          <h3 className="flex items-center gap-1.5 text-xs font-bold tracking-widest text-primary">
                            <BrainCircuit size={15} /> AI INSIGHTS
                          </h3>
                          <p className="mt-2 text-sm">{question.answer.evaluation.feedback}</p>
                        </div>
                      )}
                    </div>
                  )}
                </Card>
              ))}
            </div>
          </section>

          <Card className="mt-6 flex flex-wrap items-center justify-between gap-4 border-primary/30 p-7">
            <div>
              <h2 className="text-lg font-bold">Final Recommendation</h2>
              <p className="mt-1 max-w-xl text-sm text-foreground/70">
                Based on the AI-scored responses above, decide whether to move {candidate.data.full_name} forward.
              </p>
            </div>
            <div className="flex gap-3">
              <Button variant="destructive" onClick={() => setStatus("rejected")}>
                <X size={18} /> Reject
              </Button>
              <Button onClick={() => setStatus("shortlisted")}>
                <Star size={18} /> Shortlist
              </Button>
            </div>
          </Card>
        </>
      )}

      <Button variant="link" className="mt-4 px-0" onClick={() => navigate("/candidates")}>
        Back to candidates
      </Button>
    </>
  );
}
