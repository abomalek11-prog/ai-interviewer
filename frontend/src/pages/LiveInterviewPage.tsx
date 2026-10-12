import {
  BrainCircuit,
  CheckCircle2,
  Ear,
  Loader2,
  Mic,
  MicOff,
  MonitorUp,
  MonitorX,
  PhoneOff,
  SkipForward,
  Video,
} from "lucide-react";
import { useEffect, useRef, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";

import { interviewsApi } from "@/api/endpoints";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { useInterviewCallState } from "@/features/live-interview/useInterviewCallState";
import { useScreenShare } from "@/features/live-interview/useScreenShare";
import type { CallState } from "@/features/live-interview/interviewCallReducer";
import { useAsync } from "@/hooks/useAsync";
import { cn } from "@/lib/utils";

const SPEECH_LANGS = [
  { value: "ar-SA", label: "العربية" },
  { value: "en-US", label: "English" },
] as const;

const DEFAULT_SPEECH_LANG = "ar-SA";
const SPEECH_LANG_STORAGE_KEY = "interviewai.speechLang";

/** Remembered across sessions so the candidate never has to re-pick their language. */
function loadSpeechLang(): string {
  try {
    const saved = window.localStorage.getItem(SPEECH_LANG_STORAGE_KEY);
    if (saved && SPEECH_LANGS.some((option) => option.value === saved)) return saved;
  } catch {
    // Storage can be unavailable (private mode, blocked cookies) - fall back to the default.
  }
  return DEFAULT_SPEECH_LANG;
}

// Snapshots travel over the websocket as data URLs. A 4K screen at full size is several MB
// per turn; 1280px wide keeps code legible to the model at a fraction of that.
const MAX_FRAME_WIDTH = 1280;

const STATE_LABEL: Record<CallState, string> = {
  connecting: "Connecting...",
  ai_speaking: "AI is speaking...",
  listening: "Listening",
  candidate_speaking: "You're speaking...",
  processing: "Thinking...",
  ended: "Interview complete",
  mic_error: "Microphone unavailable",
};

export function LiveInterviewPage() {
  const { sessionId } = useParams<{ sessionId: string }>();
  const navigate = useNavigate();
  const { data: session, isLoading, error } = useAsync(() => interviewsApi.get(sessionId!), [sessionId]);

  const [speechLang, setSpeechLang] = useState<string>(loadSpeechLang);
  const videoRef = useRef<HTMLVideoElement>(null);
  const screenVideoRef = useRef<HTMLVideoElement>(null);
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const screenShare = useScreenShare();

  const captureFrame = (): string | null => {
    // A shared screen is what the candidate wants the interviewer to look at, so it wins.
    const sharing = Boolean(screenShare.stream);
    const video = sharing ? screenVideoRef.current : videoRef.current;
    const canvas = canvasRef.current;
    if (!video || !canvas || video.videoWidth === 0) return null;
    const scale = Math.min(1, MAX_FRAME_WIDTH / video.videoWidth);
    canvas.width = Math.round(video.videoWidth * scale);
    canvas.height = Math.round(video.videoHeight * scale);
    const ctx = canvas.getContext("2d");
    if (!ctx) return null;
    ctx.drawImage(video, 0, 0, canvas.width, canvas.height);
    // Higher quality for the screen: JPEG artifacts around small code glyphs hurt legibility.
    return canvas.toDataURL("image/jpeg", sharing ? 0.85 : 0.7);
  };

  const {
    state,
    liveText,
    voiceNotice,
    skipAiSpeech,
    stream,
    manualModeAvailable,
    beginTurn,
    endTurn,
    endInterview,
    retryMic,
    speechRecognitionSupported,
  } = useInterviewCallState({ sessionId, speechLang, captureFrame });

  useEffect(() => {
    if (videoRef.current) videoRef.current.srcObject = stream;
  }, [stream]);

  useEffect(() => {
    if (screenVideoRef.current) screenVideoRef.current.srcObject = screenShare.stream;
  }, [screenShare.stream]);

  // Don't leave the screen being captured after the interview is over.
  const { stop: stopScreenShare } = screenShare;
  useEffect(() => {
    if (state.call === "ended") stopScreenShare();
  }, [state.call, stopScreenShare]);

  if (isLoading) {
    return <Skeleton className="h-96 w-full" />;
  }

  if (error || !session) {
    return <p className="text-sm text-destructive">{error ?? "Interview session not found."}</p>;
  }

  const { call, transcript, notice, connectionError, overallScore } = state;

  return (
    <>
      <section className="mb-5 flex flex-wrap items-center justify-between gap-4">
        <div>
          <h1 className="text-3xl font-bold">Live AI Interview</h1>
          <p className="mt-1 text-sm text-muted-foreground">{session.difficulty} - live conversation</p>
        </div>
        <Badge variant={call === "ended" ? "success" : call === "mic_error" ? "destructive" : "warning"}>
          {STATE_LABEL[call]}
        </Badge>
      </section>

      {connectionError && <p className="mb-4 text-sm text-destructive">{connectionError}</p>}
      {screenShare.error && <p className="mb-4 text-sm text-destructive">{screenShare.error}</p>}
      {voiceNotice && <p className="mb-4 rounded-lg border border-amber-300 bg-amber-50 px-3 py-2 text-sm text-amber-800">{voiceNotice}</p>}
      {notice && <p className="mb-4 rounded-lg border border-amber-300 bg-amber-50 px-3 py-2 text-sm text-amber-800">{notice}</p>}

      {call === "mic_error" ? (
        <Card className="grid place-items-center gap-4 p-10 text-center">
          <MicOff size={40} className="text-destructive" />
          <div>
            <h2 className="text-xl font-bold">We couldn't reach your camera or microphone</h2>
            <p className="mt-1 text-muted-foreground">{connectionError}</p>
          </div>
          <Button onClick={retryMic}>Try again</Button>
        </Card>
      ) : call === "ended" ? (
        <Card className="grid place-items-center gap-4 p-10 text-center">
          <CheckCircle2 size={40} className="text-primary" />
          <div>
            <h2 className="text-2xl font-bold">Interview complete</h2>
            <p className="mt-1 text-muted-foreground">
              Overall AI score: {overallScore ?? session.overall_score ?? "-"}/100
            </p>
          </div>
          <Button onClick={() => navigate(`/candidates/${session.candidate_id}/report`)}>View full report</Button>
        </Card>
      ) : (
        <div className="grid grid-cols-1 gap-5 lg:grid-cols-[minmax(0,1fr)_minmax(280px,0.9fr)]">
          <div className="grid gap-5">
            <Card className="relative grid aspect-video place-items-center overflow-hidden bg-secondary text-white">
              <video ref={videoRef} autoPlay muted playsInline className="h-full w-full object-cover" />
              <canvas ref={canvasRef} className="hidden" />
              <video
                ref={screenVideoRef}
                autoPlay
                muted
                playsInline
                className={cn(
                  "absolute right-3 bottom-3 w-1/3 rounded-md border-2 border-white/70 bg-black object-contain shadow-lg",
                  !screenShare.stream && "hidden",
                )}
              />
              {screenShare.stream && (
                <div className="absolute top-3 right-3 flex items-center gap-1.5 rounded-full bg-sky-600/85 px-3 py-1 text-xs">
                  <MonitorUp size={14} /> Interviewer can see your screen
                </div>
              )}

              {call === "ai_speaking" && (
                <div className="absolute top-3 left-3 flex items-center gap-1.5 rounded-full bg-black/60 px-3 py-1 text-xs">
                  <BrainCircuit size={14} className="animate-pulse" /> AI speaking
                </div>
              )}
              {call === "listening" && (
                <div className="absolute top-3 left-3 flex items-center gap-1.5 rounded-full bg-black/60 px-3 py-1 text-xs">
                  <Ear size={14} /> Listening
                </div>
              )}
              {call === "candidate_speaking" && (
                <div className="absolute top-3 left-3 flex items-center gap-1.5 rounded-full bg-emerald-600/80 px-3 py-1 text-xs">
                  <Mic size={14} className="animate-pulse" /> You're speaking
                </div>
              )}
              {call === "processing" && (
                <div className="absolute top-3 left-3 flex items-center gap-1.5 rounded-full bg-black/60 px-3 py-1 text-xs">
                  <Loader2 size={14} className="animate-spin" /> Thinking
                </div>
              )}
            </Card>

            {call === "candidate_speaking" && liveText && (
              <Card className="border-primary/40 bg-primary/5 px-4 py-3">
                <p className="text-[11px] font-bold tracking-wide text-muted-foreground">HEARING YOU SAY...</p>
                <p className="mt-1 text-sm">{liveText}</p>
              </Card>
            )}

            <div className="flex flex-wrap items-center gap-3">
              {manualModeAvailable ? (
                <Button
                  variant={call === "candidate_speaking" ? "dark" : "outline"}
                  disabled={call !== "listening" && call !== "candidate_speaking" && call !== "ai_speaking"}
                  onClick={call === "candidate_speaking" ? endTurn : beginTurn}
                  className="w-fit"
                >
                  {call === "candidate_speaking" ? <Mic size={18} className="animate-pulse" /> : <Mic size={18} />}
                  {call === "candidate_speaking" ? "Tap to stop" : "Tap to speak"}
                </Button>
              ) : (
                <p className="flex items-center gap-2 rounded-lg border border-border bg-card px-3 py-2 text-sm text-muted-foreground">
                  <Ear size={16} /> Just talk naturally - no need to press anything.
                </p>
              )}
              {call === "ai_speaking" && (
                <Button variant="dark" onClick={skipAiSpeech} className="w-fit">
                  <SkipForward size={18} /> Skip - let me answer
                </Button>
              )}
              {screenShare.supported && (
                <Button
                  variant="outline"
                  onClick={screenShare.stream ? screenShare.stop : () => void screenShare.start()}
                  className="w-fit"
                >
                  {screenShare.stream ? <MonitorX size={18} /> : <MonitorUp size={18} />}
                  {screenShare.stream ? "Stop sharing" : "Share screen"}
                </Button>
              )}
              <Button variant="outline" onClick={endInterview} className="w-fit">
                <PhoneOff size={18} /> End interview
              </Button>
              {speechRecognitionSupported && (
                <select
                  value={speechLang}
                  onChange={(e) => {
                    setSpeechLang(e.target.value);
                    try {
                      window.localStorage.setItem(SPEECH_LANG_STORAGE_KEY, e.target.value);
                    } catch {
                      // Non-fatal: the choice just won't survive a reload.
                    }
                  }}
                  disabled={call === "candidate_speaking"}
                  className="h-9 rounded-md border border-border bg-background px-2 text-sm"
                  aria-label="Speech language"
                >
                  {SPEECH_LANGS.map((option) => (
                    <option key={option.value} value={option.value}>
                      {option.label}
                    </option>
                  ))}
                </select>
              )}
            </div>
          </div>

          <div className="grid gap-4">
            <Card className="max-h-[520px] overflow-y-auto p-5">
              <h3 className="text-sm font-bold">Transcript</h3>
              <div className="mt-3 grid gap-3">
                {transcript.length === 0 && (
                  <p className="flex items-center gap-2 text-sm text-muted-foreground">
                    <Video size={16} /> The conversation will appear here.
                  </p>
                )}
                {transcript.map((entry) => (
                  <div
                    key={entry.id}
                    className={cn(
                      "rounded-lg border border-border px-3 py-2 text-sm",
                      entry.role === "ai" ? "bg-primary/5" : "bg-secondary/5",
                    )}
                  >
                    <p className="mb-1 text-[11px] font-bold tracking-wide text-muted-foreground">
                      {entry.role === "ai" ? "INTERVIEWER" : "YOU"}
                    </p>
                    {entry.text}
                  </div>
                ))}
              </div>
            </Card>
          </div>
        </div>
      )}
    </>
  );
}
