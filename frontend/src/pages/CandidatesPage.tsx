import { useNavigate } from "react-router-dom";

import { candidatesApi } from "@/api/endpoints";
import { Badge } from "@/components/ui/badge";
import { Card, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { useAsync } from "@/hooks/useAsync";
import type { CandidateStatus } from "@/types/api";

const statusBadge: Record<CandidateStatus, "success" | "warning" | "neutral" | "destructive"> = {
  new: "neutral",
  interviewing: "warning",
  shortlisted: "success",
  hired: "success",
  rejected: "destructive",
};

export function CandidatesPage() {
  const navigate = useNavigate();
  const candidates = useAsync(() => candidatesApi.list(), []);

  return (
    <>
      <section className="mb-5">
        <h1 className="text-4xl leading-tight font-bold">Candidates</h1>
        <p className="mt-1.5 max-w-2xl text-base text-foreground/70">
          Every candidate across your AI jobs, with their latest interview score.
        </p>
      </section>

      <Card className="overflow-hidden">
        <div className="grid grid-cols-[minmax(220px,1.2fr)_minmax(160px,0.9fr)_minmax(100px,0.5fr)_minmax(100px,0.5fr)] items-center bg-muted px-6 py-2.5 text-xs font-extrabold tracking-[2px] text-foreground/70">
          <span>CANDIDATE</span>
          <span>JOB</span>
          <span>SCORE</span>
          <span>STATUS</span>
        </div>

        {candidates.isLoading && <Skeleton className="m-4 h-16" />}
        {!candidates.isLoading && candidates.data?.length === 0 && (
          <p className="p-6 text-sm text-muted-foreground">No candidates yet.</p>
        )}
        {candidates.data?.map((candidate) => (
          <button
            key={candidate.id}
            onClick={() => navigate(`/candidates/${candidate.id}/report`)}
            className="grid w-full grid-cols-[minmax(220px,1.2fr)_minmax(160px,0.9fr)_minmax(100px,0.5fr)_minmax(100px,0.5fr)] items-center gap-2 border-t border-border px-6 py-4 text-left hover:bg-muted/40"
          >
            <div>
              <strong className="block text-[15px]">{candidate.full_name}</strong>
              <p className="mt-0.5 text-[13px] text-foreground/70">{candidate.email}</p>
            </div>
            <span className="text-sm text-foreground/80">{candidate.job_title}</span>
            <span className="font-mono text-sm font-extrabold">{candidate.latest_score ?? "-"}</span>
            <Badge variant={statusBadge[candidate.status]}>{candidate.status}</Badge>
          </button>
        ))}
      </Card>
    </>
  );
}
