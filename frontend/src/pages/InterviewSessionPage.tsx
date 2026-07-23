import { BrainCircuit, CheckCircle2, Mic, MicOff, Sparkles, Video, VideoOff } from "lucide-react";
import { useEffect, useRef, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";

import { extractErrorMessage } from "@/api/client";
import { aiApi, interviewsApi } from "@/api/endpoints";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Progress } from "@/components/ui/progress";
import { Skeleton } from "@/components/ui/skeleton";
import { Textarea } from "@/components/ui/textarea";
import { useAsync } from "@/hooks/useAsync";

export function InterviewSessionPage() {
  const { sessionId } = useParams<{ sessionId: string }>();
  const navigate = useNavigate();
  const { data: session, isLoading, error, refetch } = useAsync(() => interviewsApi.get(sessionId!), [sessionId]);

  const [transcript, setTranscript] = useState("");
  const [submitError, setSubmitError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [cameraOn, setCameraOn] = useState(false);
  const videoRef = useRef<HTMLVideoElement>(null);
  const streamRef = useRef<MediaStream | null>(null);

  const [isRecording, setIsRecording] = useState(false);
  const [isTranscribing, setIsTranscribing] = useState(false);
  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const audioChunksRef = useRef<Blob[]>([]);
  const micStreamRef = useRef<MediaStream | null>(null);

  const currentQuestion = session?.questions.find((q) => !q.answer) ?? null;
  const answeredCount = session ? session.questions.filter((q) => q.answer).length : 0;
  const totalCount = session?.questions.length ?? 0;

  useEffect(() => {
    return () => {
      streamRef.current?.getTracks().forEach((track) => track.stop());
      micStreamRef.current?.getTracks().forEach((track) => track.stop());
    };
  }, []);

  const toggleCamera = async () => {
    if (cameraOn) {
      streamRef.current?.getTracks().forEach((track) => track.stop());
      streamRef.current = null;
      setCameraOn(false);
      return;
    }
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ video: true, audio: false });
      streamRef.current = stream;
      if (videoRef.current) videoRef.current.srcObject = stream;
      setCameraOn(true);
    } catch {
      setSubmitError("Could not access the camera. Check your browser permissions.");
    }
  };

  const toggleRecording = async () => {
    if (isRecording) {
      mediaRecorderRef.current?.stop();
      return;
    }

    setSubmitError(null);
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      micStreamRef.current = stream;
      audioChunksRef.current = [];

      const recorder = new MediaRecorder(stream);
      mediaRecorderRef.current = recorder;

      recorder.ondataavailable = (e) => {
        if (e.data.size > 0) audioChunksRef.current.push(e.data);
      };

      recorder.onstop = async () => {
        micStreamRef.current?.getTracks().forEach((track) => track.stop());
        micStreamRef.current = null;
        setIsRecording(false);

        const audioBlob = new Blob(audioChunksRef.current, { type: recorder.mimeType || "audio/webm" });
        audioChunksRef.current = [];
        if (audioBlob.size === 0) return;

        setIsTranscribing(true);
        try {
          const { text } = await aiApi.transcribe(audioBlob);
          setTranscript((prev) => (prev.trim() ? `${prev.trim()} ${text}` : text));
        } catch (err) {
          setSubmitError(extractErrorMessage(err, "Could not transcribe your answer"));
        } finally {
          setIsTranscribing(false);
        }
      };

      recorder.start();
      setIsRecording(true);
    } catch {
      setSubmitError("Could not access the microphone. Check your browser permissions.");
    }
  };

  const submitAnswer = async () => {
    if (!session || !currentQuestion || !transcript.trim()) return;
    setSubmitError(null);
    setIsSubmitting(true);
    try {
      await interviewsApi.submitAnswer(session.id, { question_id: currentQuestion.id, transcript });
      setTranscript("");
      refetch();
    } catch (err) {
      setSubmitError(extractErrorMessage(err, "Could not submit your answer"));
    } finally {
      setIsSubmitting(false);
    }
  };

  if (isLoading) {
    return <Skeleton className="h-96 w-full" />;
  }

  if (error || !session) {
    return <p className="text-sm text-destructive">{error ?? "Interview session not found."}</p>;
  }

  const lastAnswered = [...session.questions].reverse().find((q) => q.answer)?.answer ?? null;

  return (
    <>
      <section className="mb-5 flex flex-wrap items-center justify-between gap-4">
        <div>
          <h1 className="text-3xl font-bold">Live Interview Session</h1>
          <p className="mt-1 text-sm text-muted-foreground">
            {session.difficulty} - {session.interview_type} - {answeredCount}/{totalCount} answered
          </p>
        </div>
        <Badge variant={session.status === "completed" ? "success" : "warning"}>{session.status.replace("_", " ")}</Badge>
      </section>

      <Progress value={totalCount ? (answeredCount / totalCount) * 100 : 0} className="mb-6" />

      {session.status === "completed" ? (
        <Card className="grid place-items-center gap-4 p-10 text-center">
          <CheckCircle2 size={40} className="text-primary" />
          <div>
            <h2 className="text-2xl font-bold">Interview complete</h2>
            <p className="mt-1 text-muted-foreground">Overall AI score: {session.overall_score}/100</p>
          </div>
          <Button onClick={() => navigate(`/candidates/${session.candidate_id}/report`)}>View full report</Button>
        </Card>
      ) : (
        <div className="grid grid-cols-1 gap-5 lg:grid-cols-[minmax(0,1fr)_minmax(280px,0.9fr)]">
          <div className="grid gap-5">
            <Card className="grid aspect-video place-items-center overflow-hidden bg-secondary text-white">
              {cameraOn ? (
                <video ref={videoRef} autoPlay muted playsInline className="h-full w-full object-cover" />
              ) : (
                <div className="text-center text-white/60">
                  <Video size={36} className="mx-auto mb-2" />
                  <p className="text-sm">Camera preview off</p>
                </div>
              )}
            </Card>
            <div className="flex flex-wrap gap-2">
              <Button variant="outline" onClick={toggleCamera} className="w-fit">
                {cameraOn ? <VideoOff size={18} /> : <Video size={18} />}
                {cameraOn ? "Turn camera off" : "Turn camera on"}
              </Button>
              <Button variant="outline" onClick={toggleRecording} disabled={isTranscribing} className="w-fit">
                {isRecording ? <MicOff size={18} /> : <Mic size={18} />}
                {isTranscribing ? "Transcribing..." : isRecording ? "Stop recording" : "Record answer"}
              </Button>
            </div>

            {currentQuestion && (
              <Card className="p-6">
                <p className="text-xs font-bold tracking-widest text-primary">
                  QUESTION {currentQuestion.order_index + 1} OF {totalCount}
                </p>
                <h2 className="mt-2 text-xl font-bold">{currentQuestion.prompt}</h2>
                <div className="mt-2 flex flex-wrap gap-1.5">
                  {currentQuestion.expected_topics.map((topic) => (
                    <Badge key={topic} variant="neutral">
                      {topic}
                    </Badge>
                  ))}
                </div>

                {submitError && <p className="mt-4 text-sm text-destructive">{submitError}</p>}

                <Textarea
                  className="mt-4"
                  placeholder="Type (or paste your spoken) answer here..."
                  rows={6}
                  value={transcript}
                  onChange={(e) => setTranscript(e.target.value)}
                />
                <Button className="mt-3" onClick={submitAnswer} disabled={isSubmitting || isTranscribing || !transcript.trim()}>
                  {isSubmitting ? "Scoring with AI..." : "Submit Answer"}
                </Button>
              </Card>
            )}
          </div>

          <div className="grid gap-4">
            <Card className="p-5">
              <h3 className="text-sm font-bold">Questions</h3>
              <div className="mt-3 grid gap-2">
                {session.questions.map((q) => (
                  <div key={q.id} className="flex items-center justify-between rounded-lg border border-border px-3 py-2 text-sm">
                    <span className="truncate pr-2">{q.prompt}</span>
                    {q.answer ? (
                      <Badge variant="success">{q.answer.evaluation?.score ?? "-"}</Badge>
                    ) : (
                      <Badge variant="neutral">pending</Badge>
                    )}
                  </div>
                ))}
              </div>
            </Card>

            {lastAnswered?.evaluation && (
              <Card className="border-primary/40 bg-primary/5 p-5">
                <div className="flex items-center gap-2 text-primary">
                  <BrainCircuit size={18} />
                  <h3 className="text-sm font-bold">AI Insight - last answer</h3>
                </div>
                <p className="mt-2 text-2xl font-bold">{lastAnswered.evaluation.score}/100</p>
                <p className="mt-2 text-sm text-foreground/80">{lastAnswered.evaluation.feedback}</p>
                <div className="mt-3 grid gap-1 text-xs">
                  {lastAnswered.evaluation.strengths.map((s) => (
                    <div key={s} className="flex items-center gap-1.5 text-success">
                      <Sparkles size={12} /> {s}
                    </div>
                  ))}
                  {lastAnswered.evaluation.improvements.map((s) => (
                    <div key={s} className="flex items-center gap-1.5 text-warning">
                      <Sparkles size={12} /> {s}
                    </div>
                  ))}
                </div>
              </Card>
            )}
          </div>
        </div>
      )}
    </>
  );
}
