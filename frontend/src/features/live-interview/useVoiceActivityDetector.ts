import { useEffect, useRef, useState } from "react";

// Neural (Silero) VAD - far more robust to background noise than a raw RMS/volume
// threshold, and its redemption/min-speech-frame knobs are what let a candidate
// pause briefly mid-sentence without the turn being cut off.
import { MicVAD } from "@ricky0123/vad-web";

export interface VadThresholds {
  /** Frame-level probability above which audio is considered speech (0-1). Higher = less sensitive to noise. */
  positiveSpeechThreshold: number;
  /** Probability below which speech is considered to have ended (0-1). */
  negativeSpeechThreshold: number;
  /** Consecutive speech frames required before a segment counts as real speech (filters out blips). */
  minSpeechFrames: number;
  /** Consecutive silent frames tolerated before ending a speech segment (lets the candidate pause and continue). */
  redemptionFrames: number;
}

export const DEFAULT_VAD_THRESHOLDS: VadThresholds = {
  positiveSpeechThreshold: 0.6,
  negativeSpeechThreshold: 0.45,
  minSpeechFrames: 3,
  redemptionFrames: 24, // ~768ms at the model's 32ms frame size - tolerates a mid-sentence breath/pause
};

export type VadStatus = "idle" | "loading" | "ready" | "error";

interface UseVoiceActivityDetectorOptions {
  /** Gate for when VAD should acquire its own (audio-only) stream and start listening. */
  enabled: boolean;
  thresholds?: Partial<VadThresholds>;
  onSpeechStart: () => void;
  onSpeechEnd: (audio: Float32Array) => void;
  onMisfire?: () => void;
}

/**
 * Thin wrapper around @ricky0123/vad-web. Knows only "speech started" / "speech ended" /
 * "misfire" - nothing about interview state, playback, or the socket. Reports init failure
 * via `status` so callers can fall back to a manual push-to-talk control.
 *
 * Deliberately lets MicVAD acquire and own its own audio-only MediaStream (its documented,
 * stable code path) rather than sharing the page's video+audio stream - that keeps this
 * hook fully independent of `useMicStream` and avoids depending on unconfirmed cross-stream
 * plumbing. The browser reuses the already-granted mic permission for the second stream.
 */
export function useVoiceActivityDetector({ enabled, thresholds, onSpeechStart, onSpeechEnd, onMisfire }: UseVoiceActivityDetectorOptions) {
  const [status, setStatus] = useState<VadStatus>("idle");
  const vadRef = useRef<Awaited<ReturnType<typeof MicVAD.new>> | null>(null);
  const callbacksRef = useRef({ onSpeechStart, onSpeechEnd, onMisfire });
  callbacksRef.current = { onSpeechStart, onSpeechEnd, onMisfire };

  useEffect(() => {
    if (!enabled) return;
    let cancelled = false;
    setStatus("loading");

    const merged = { ...DEFAULT_VAD_THRESHOLDS, ...thresholds };

    MicVAD.new({
      positiveSpeechThreshold: merged.positiveSpeechThreshold,
      negativeSpeechThreshold: merged.negativeSpeechThreshold,
      minSpeechFrames: merged.minSpeechFrames,
      redemptionFrames: merged.redemptionFrames,
      onSpeechStart: () => callbacksRef.current.onSpeechStart(),
      onSpeechEnd: (audio: Float32Array) => callbacksRef.current.onSpeechEnd(audio),
      onVADMisfire: () => callbacksRef.current.onMisfire?.(),
    })
      .then((vad) => {
        if (cancelled) {
          vad.destroy();
          return;
        }
        vadRef.current = vad;
        vad.start();
        setStatus("ready");
      })
      .catch(() => {
        if (!cancelled) setStatus("error");
      });

    return () => {
      cancelled = true;
      vadRef.current?.pause();
      vadRef.current?.destroy();
      vadRef.current = null;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [enabled]);

  const pause = () => vadRef.current?.pause();
  const resume = () => vadRef.current?.start();

  return { status, pause, resume };
}
