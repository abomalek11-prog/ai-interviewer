import { useEffect, useRef, useState } from "react";

// Neural (Silero) VAD - far more robust to background noise than a raw RMS/volume
// threshold, and its redemption/min-speech-frame knobs are what let a candidate
// pause briefly mid-sentence without the turn being cut off.
import { MicVAD } from "@ricky0123/vad-web";

// Keep in step with package.json: @ricky0123/vad-web 0.0.24 ships with onnxruntime-web 1.14.0.
const VAD_ASSET_PATH = "https://cdn.jsdelivr.net/npm/@ricky0123/vad-web@0.0.24/dist/";
const ONNX_WASM_PATH = "https://cdn.jsdelivr.net/npm/onnxruntime-web@1.14.0/dist/";

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
  // ~320ms at the model's 32ms frame size. Three frames (~96ms) let a cough, a chair
  // creak or a one-word "aha" open a turn, which the backend then had to treat as an answer.
  minSpeechFrames: 10,
  // ~1.9s. People pause well past 768ms while thinking mid-answer, and the old value cut
  // them off and submitted the half-sentence as their answer.
  redemptionFrames: 60,
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
      // Pinned to the installed versions. The library's default points at vad-web@latest
      // on the CDN, so a new upstream release could silently mismatch this bundle's code.
      baseAssetPath: VAD_ASSET_PATH,
      onnxWASMBasePath: ONNX_WASM_PATH,
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
