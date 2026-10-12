import { useCallback, useEffect, useReducer, useRef, useState } from "react";

import { useAiAudioPlayer } from "./useAiAudioPlayer";
import type { CallEvent, TransitionDeps } from "./interviewCallReducer";
import { initialInterviewCallState, transition } from "./interviewCallReducer";
import { useLiveInterviewSocket } from "./useLiveInterviewSocket";
import { useMicStream } from "./useMicStream";
import { DEFAULT_VAD_THRESHOLDS, useVoiceActivityDetector, type VadThresholds } from "./useVoiceActivityDetector";

// eslint-disable-next-line @typescript-eslint/no-explicit-any
const SpeechRecognitionImpl: any =
  typeof window !== "undefined" ? (window as any).SpeechRecognition ?? (window as any).webkitSpeechRecognition : undefined;

interface UseInterviewCallStateOptions {
  sessionId: string | undefined;
  speechLang: string;
  captureFrame?: () => string | null;
  vadThresholds?: Partial<VadThresholds>;
}

/**
 * Orchestrates the mic stream, VAD, AI audio playback, and the live-interview socket
 * into a single call state machine. This is the only piece that wires those four
 * independent hooks together - each of them stays testable/replaceable in isolation.
 */
export function useInterviewCallState({ sessionId, speechLang, captureFrame, vadThresholds }: UseInterviewCallStateOptions) {
  const [micRetryKey, setMicRetryKey] = useState(0);
  const mic = useMicStream(true, micRetryKey);

  // Declared before useReducer: React replays queued actions through the reducer at the
  // useReducer call site, so the closure below must not read a binding declared further
  // down this function. The placeholders are only ever live on the first render, before
  // anything can have dispatched; every later render reuses the previous render's deps.
  const depsRef = useRef<TransitionDeps>({ stopAiPlayback: () => {}, submitTurn: () => {} });

  const [state, dispatchRaw] = useReducer(
    (s: typeof initialInterviewCallState, event: CallEvent) => transition(s, event, depsRef.current),
    initialInterviewCallState,
  );
  const stateRef = useRef(state);
  stateRef.current = state;
  const dispatch = useCallback((event: CallEvent) => dispatchRaw(event), []);

  const langRef = useRef(speechLang);
  langRef.current = speechLang;
  const lastAiTextRef = useRef("");
  const captureFrameRef = useRef(captureFrame);
  captureFrameRef.current = captureFrame;

  const [liveText, setLiveText] = useState("");
  const [voiceNotice, setVoiceNotice] = useState<string | null>(null);

  // Assigned once the VAD exists further down; the player callbacks only fire later.
  const vadControlRef = useRef<{ pause: () => void; resume: () => void } | null>(null);
  // True while the VAD is paused because the OS speech engine is talking: that audio
  // bypasses echo cancellation, so the mic would hear the AI and "barge in" on its own
  // first word, cutting every reply off.
  const vadMutedForAiRef = useRef(false);

  const player = useAiAudioPlayer({
    lang: speechLang,
    onEnded: () => dispatch({ type: "ai_audio_ended" }),
    onPlaybackStart: (source) => {
      if (source !== "browser" || vadMutedForAiRef.current) return;
      vadMutedForAiRef.current = true;
      vadControlRef.current?.pause();
    },
    onVoiceUnavailable: () =>
      setVoiceNotice(
        "No voice for this language is installed in your browser, so replies are shown as text only. " +
          "Microsoft Edge includes Arabic voices.",
      ),
  });

  const socket = useLiveInterviewSocket(
    sessionId,
    {
      onAiText: (text) => {
        lastAiTextRef.current = text;
        dispatch({ type: "ai_text", text });
      },
      onAiAudio: (bytes) => player.playAudioBytes(bytes, lastAiTextRef.current),
      onTranscript: (text) => dispatch({ type: "transcript", text }),
      onSummary: (overallScore) => dispatch({ type: "summary", overallScore }),
      onNotice: (message) => dispatch({ type: "notice", message }),
      onError: (message) => dispatch({ type: "socket_error", message }),
      onOpen: () => {},
      onClose: () => dispatch({ type: "socket_closed" }),
    },
    speechLang,
  );

  // The handshake carries the starting language; this keeps the AI in step when the
  // candidate switches language mid-interview, without dropping the connection.
  // Keyed off the language alone - `socket` is a fresh object every render, so depending
  // on it here would re-send on every re-render.
  const sentLangRef = useRef(speechLang);
  const sendLanguageRef = useRef(socket.sendLanguage);
  sendLanguageRef.current = socket.sendLanguage;
  useEffect(() => {
    if (sentLangRef.current === speechLang) return;
    sentLangRef.current = speechLang;
    sendLanguageRef.current(speechLang);
  }, [speechLang]);

  const submitTurn = useCallback<TransitionDeps["submitTurn"]>(
    (input) => {
      const frame = captureFrameRef.current?.();
      if (frame) socket.sendFrame(frame);
      if (input.text) {
        socket.sendUserText(input.text);
      } else if (input.audioBlob) {
        input.audioBlob.arrayBuffer().then((buf) => socket.sendAudio(buf));
      }
    },
    [socket],
  );

  depsRef.current = { stopAiPlayback: player.stop, submitTurn };

  // Candidate audio capture: a plain MediaRecorder over the mic's audio track, started/stopped
  // by whatever detects the turn boundary (VAD normally, a manual button in the fallback path).
  // Kept as the universal fallback so the wire format to the backend never changes.
  const recorderRef = useRef<MediaRecorder | null>(null);
  const chunksRef = useRef<Blob[]>([]);

  const startCapture = useCallback(() => {
    if (!mic.stream) return;
    const audioStream = new MediaStream(mic.stream.getAudioTracks());
    const recorder = new MediaRecorder(audioStream);
    chunksRef.current = [];
    recorder.ondataavailable = (e) => {
      if (e.data.size > 0) chunksRef.current.push(e.data);
    };
    recorder.start();
    recorderRef.current = recorder;
  }, [mic.stream]);

  const stopCaptureAndGetBlob = useCallback((): Promise<Blob> => {
    return new Promise((resolve) => {
      const recorder = recorderRef.current;
      if (!recorder) {
        resolve(new Blob());
        return;
      }
      recorder.onstop = () => resolve(new Blob(chunksRef.current, { type: recorder.mimeType || "audio/webm" }));
      recorder.stop();
      recorderRef.current = null;
    });
  }, []);

  // Browser speech recognition (Chrome/Edge): free live captions + a text transcript that,
  // when available, is sent instead of the recorded blob (matches prior behavior).
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const recognitionRef = useRef<any>(null);
  const recognizedTextRef = useRef("");

  const startRecognitionCaptioning = useCallback(() => {
    if (!SpeechRecognitionImpl) return;
    const recognition = new SpeechRecognitionImpl();
    recognition.lang = langRef.current;
    recognition.continuous = true;
    recognition.interimResults = true;
    recognizedTextRef.current = "";
    setLiveText("");

    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    recognition.onresult = (event: any) => {
      let finalText = "";
      let interim = "";
      for (let i = 0; i < event.results.length; i += 1) {
        const result = event.results[i];
        if (result.isFinal) finalText += `${result[0].transcript} `;
        else interim += result[0].transcript;
      }
      recognizedTextRef.current = finalText.trim();
      setLiveText(`${finalText}${interim}`.trim());
    };
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    recognition.onerror = (event: any) => {
      if (event.error === "not-allowed" || event.error === "service-not-allowed") {
        dispatch({ type: "notice", message: "Live captions were blocked - your answer will still be transcribed on submit." });
      }
    };

    recognitionRef.current = recognition;
    recognition.start();
  }, [dispatch]);

  const stopRecognitionAndGetFinalText = useCallback((): Promise<string> => {
    return new Promise((resolve) => {
      const recognition = recognitionRef.current;
      if (!recognition) {
        resolve("");
        return;
      }
      recognition.onend = () => {
        setLiveText("");
        resolve(recognizedTextRef.current);
      };
      recognition.stop();
      recognitionRef.current = null;
    });
  }, []);

  const beginTurn = useCallback(() => {
    const current = stateRef.current.call;
    if (current !== "listening" && current !== "ai_speaking") return;
    dispatch({ type: "speech_start" });
    startCapture();
    startRecognitionCaptioning();
  }, [dispatch, startCapture, startRecognitionCaptioning]);

  const endTurn = useCallback(async () => {
    if (stateRef.current.call !== "candidate_speaking") return;
    const [recognizedText, blob] = await Promise.all([stopRecognitionAndGetFinalText(), stopCaptureAndGetBlob()]);
    if (recognizedText.trim()) {
      dispatch({ type: "speech_end", text: recognizedText.trim() });
    } else if (blob.size > 0) {
      dispatch({ type: "speech_end", audioBlob: blob });
    } else {
      dispatch({ type: "speech_end" });
    }
  }, [dispatch, stopCaptureAndGetBlob, stopRecognitionAndGetFinalText]);

  // VAD's captured Float32Array segment is intentionally unused for submission - timing only.
  // Capture/recognition (above) is what actually produces the payload sent to the backend.
  const vad = useVoiceActivityDetector({
    enabled: mic.permissionState === "granted",
    thresholds: vadThresholds ?? DEFAULT_VAD_THRESHOLDS,
    onSpeechStart: beginTurn,
    onSpeechEnd: () => {
      void endTurn();
    },
    onMisfire: () => dispatch({ type: "vad_misfire" }),
  });
  vadControlRef.current = { pause: vad.pause, resume: vad.resume };

  // The model often finishes loading while the opening greeting is already being spoken,
  // and it starts listening on load - mute it straight away in that case too.
  useEffect(() => {
    if (vad.status === "ready" && vadMutedForAiRef.current) vadControlRef.current?.pause();
  }, [vad.status]);

  // Un-mute the VAD once the AI has stopped talking (finished, skipped or interrupted).
  // The short delay keeps the tail of the speech engine's audio from opening a turn.
  useEffect(() => {
    if (state.call === "ai_speaking" || !vadMutedForAiRef.current) return;
    const timer = window.setTimeout(() => {
      vadMutedForAiRef.current = false;
      vadControlRef.current?.resume();
    }, 300);
    return () => window.clearTimeout(timer);
  }, [state.call]);

  /** Candidate cuts the AI short to answer (the VAD can't do it while the AI is muted out). */
  const skipAiSpeech = useCallback(() => {
    if (stateRef.current.call !== "ai_speaking") return;
    player.stop();
    dispatch({ type: "ai_audio_ended" });
  }, [dispatch, player]);

  useEffect(() => {
    if (mic.error) dispatch({ type: "mic_error", message: mic.error });
  }, [mic.error, dispatch]);

  useEffect(() => {
    return () => {
      recorderRef.current?.stop();
      recognitionRef.current?.abort?.();
    };
  }, []);

  const endInterview = useCallback(() => socket.sendEnd(), [socket]);
  const retryMic = useCallback(() => setMicRetryKey((k) => k + 1), []);

  const manualModeAvailable = vad.status === "error";

  return {
    state,
    liveText,
    voiceNotice,
    skipAiSpeech,
    stream: mic.stream,
    vadStatus: vad.status,
    manualModeAvailable,
    beginTurn,
    endTurn,
    endInterview,
    retryMic,
    speechRecognitionSupported: Boolean(SpeechRecognitionImpl),
  };
}
