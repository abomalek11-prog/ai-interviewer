import { BrainCircuit } from "lucide-react";
import type { ReactNode } from "react";

export function AuthLayout({ children }: { children: ReactNode }) {
  return (
    <main className="grid min-h-screen grid-cols-1 bg-[#f7f9fb] lg:grid-cols-[1.08fr_0.72fr]">
      <section className="hidden flex-col justify-between bg-[#101827] bg-[image:linear-gradient(135deg,rgba(8,122,79,0.1),transparent_42%)] p-14 text-white lg:flex">
        <div className="flex items-center gap-3">
          <div className="grid size-[42px] place-items-center rounded-lg bg-white/10">
            <BrainCircuit size={24} />
          </div>
          <div>
            <strong className="block text-2xl leading-none">InterviewAI</strong>
            <span className="mt-1 block font-mono text-[10px] tracking-[2px] text-white/70">AI-DRIVEN INSIGHTS</span>
          </div>
        </div>
        <div className="max-w-[720px]">
          <p className="font-mono text-sm font-extrabold tracking-[2px] text-primary">HIRING INTELLIGENCE PLATFORM</p>
          <h1 className="mt-3 text-5xl leading-[1.05] font-bold lg:text-6xl">
            Assess technical talent with consistent AI-backed evidence.
          </h1>
          <div className="mt-8 flex flex-wrap gap-3">
            {["32 active jobs", "148 candidate assessments", "91% reviewer agreement"].map((item) => (
              <span key={item} className="rounded-full border border-white/20 bg-white/10 px-3.5 py-2.5 text-sm">
                {item}
              </span>
            ))}
          </div>
        </div>
        <div />
      </section>

      <section className="flex flex-col justify-center gap-6 border-l border-border bg-white p-8 sm:p-14">
        <div className="mx-auto w-full max-w-md">{children}</div>
      </section>
    </main>
  );
}
