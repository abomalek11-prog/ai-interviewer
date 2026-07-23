import { analyticsApi } from "@/api/endpoints";
import { Card, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { useAsync } from "@/hooks/useAsync";

export function AnalyticsPage() {
  const analytics = useAsync(() => analyticsApi.summary(), []);
  const maxTrend = Math.max(1, ...(analytics.data?.trend_30d.map((p) => p.completed) ?? [1]));

  if (analytics.isLoading) return <Skeleton className="h-96 w-full" />;
  if (analytics.error || !analytics.data) return <p className="text-sm text-destructive">{analytics.error}</p>;

  const data = analytics.data;

  return (
    <>
      <section className="mb-6">
        <h1 className="text-4xl leading-tight font-bold">Analytics</h1>
        <p className="mt-1.5 max-w-2xl text-base text-foreground/70">
          Aggregate performance across every AI-scored interview you've run.
        </p>
      </section>

      <section className="grid grid-cols-1 gap-4 sm:grid-cols-4">
        {[
          { label: "TOTAL INTERVIEWS", value: data.total_interviews },
          { label: "COMPLETED", value: data.completed_interviews },
          { label: "SUCCESS RATE", value: `${data.success_rate}%` },
          { label: "AVG AI SCORE", value: data.avg_ai_score },
        ].map((metric) => (
          <Card key={metric.label} className="p-5">
            <p className="text-xs font-bold tracking-[2px] text-foreground/60">{metric.label}</p>
            <strong className="mt-2 block text-3xl">{metric.value}</strong>
          </Card>
        ))}
      </section>

      <section className="mt-5 grid grid-cols-1 gap-5 lg:grid-cols-[minmax(0,2fr)_minmax(280px,1fr)]">
        <Card className="p-6">
          <CardTitle>Completion Trend (30 days)</CardTitle>
          <div className="mt-5 flex h-56 items-end gap-1.5">
            {data.trend_30d.length === 0 && <p className="self-center text-sm text-muted-foreground">No data yet.</p>}
            {data.trend_30d.map((point) => (
              <div key={point.date} className="flex flex-1 flex-col items-center gap-1" title={`${point.date}: ${point.completed}`}>
                <div className="w-full rounded-t bg-primary/80" style={{ height: `${Math.max(6, (point.completed / maxTrend) * 100)}%` }} />
              </div>
            ))}
          </div>
        </Card>

        <Card className="p-6">
          <CardTitle>Jobs by Seniority</CardTitle>
          <div className="mt-5 grid gap-3">
            {data.difficulty_breakdown.length === 0 && <p className="text-sm text-muted-foreground">No jobs yet.</p>}
            {data.difficulty_breakdown.map((item) => (
              <div key={item.seniority}>
                <div className="flex justify-between text-sm">
                  <span>{item.seniority}</span>
                  <b>{item.percentage}%</b>
                </div>
                <div className="mt-1.5 h-2 rounded-full bg-muted">
                  <div className="h-full rounded-full bg-primary" style={{ width: `${item.percentage}%` }} />
                </div>
              </div>
            ))}
          </div>
        </Card>
      </section>
    </>
  );
}
