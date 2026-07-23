import { useEffect, useRef, useState } from "react";

export type MicPermissionState = "pending" | "granted" | "denied" | "unavailable";

interface MicStreamState {
  stream: MediaStream | null;
  permissionState: MicPermissionState;
  error: string | null;
}

function describeError(err: unknown): { state: MicPermissionState; message: string } {
  if (typeof navigator === "undefined" || !navigator.mediaDevices?.getUserMedia) {
    return { state: "unavailable", message: "This browser doesn't support microphone/camera access." };
  }
  if (err instanceof DOMException) {
    if (err.name === "NotAllowedError" || err.name === "SecurityError") {
      return { state: "denied", message: "Camera/microphone access was blocked. Allow access in your browser settings and retry." };
    }
    if (err.name === "NotFoundError") {
      return { state: "unavailable", message: "No camera or microphone was found on this device." };
    }
    if (err.name === "NotReadableError") {
      return { state: "unavailable", message: "Your camera or microphone is already in use by another application." };
    }
  }
  return { state: "unavailable", message: "Could not access your camera and microphone." };
}

/**
 * Owns the getUserMedia stream for the interview call: acquisition, permission/error
 * classification, and teardown. Knows nothing about VAD, playback, or the socket.
 */
export function useMicStream(enabled: boolean, retryKey: number) {
  const [state, setState] = useState<MicStreamState>({ stream: null, permissionState: "pending", error: null });
  const streamRef = useRef<MediaStream | null>(null);

  useEffect(() => {
    if (!enabled) return;
    let cancelled = false;

    navigator.mediaDevices
      .getUserMedia({
        video: true,
        // Explicit rather than relying on browser defaults: echo cancellation keeps the AI's
        // own speaker output from re-triggering the VAD as "candidate speech" on non-headphone
        // setups, and noise suppression/AGC reduce false triggers from background noise.
        audio: { echoCancellation: true, noiseSuppression: true, autoGainControl: true },
      })
      .then((stream) => {
        if (cancelled) {
          stream.getTracks().forEach((track) => track.stop());
          return;
        }
        streamRef.current = stream;
        setState({ stream, permissionState: "granted", error: null });
      })
      .catch((err) => {
        if (cancelled) return;
        const { state: permissionState, message } = describeError(err);
        setState({ stream: null, permissionState, error: message });
      });

    return () => {
      cancelled = true;
      streamRef.current?.getTracks().forEach((track) => track.stop());
      streamRef.current = null;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [enabled, retryKey]);

  return state;
}
