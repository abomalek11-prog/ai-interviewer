import { useCallback, useEffect, useRef, useState } from "react";

/**
 * Owns the optional screen-share stream only. While it is active, the snapshot sent with
 * each turn is taken from the shared screen instead of the webcam, so the interviewer can
 * read the candidate's code, diagram or whiteboard.
 */
export function useScreenShare() {
  const [stream, setStream] = useState<MediaStream | null>(null);
  const [error, setError] = useState<string | null>(null);
  const streamRef = useRef<MediaStream | null>(null);

  const stop = useCallback(() => {
    streamRef.current?.getTracks().forEach((track) => track.stop());
    streamRef.current = null;
    setStream(null);
  }, []);

  const start = useCallback(async () => {
    setError(null);
    try {
      const display = await navigator.mediaDevices.getDisplayMedia({ video: true, audio: false });
      // The browser's own "Stop sharing" bar ends the track without going through us.
      display.getVideoTracks()[0]?.addEventListener("ended", stop);
      streamRef.current = display;
      setStream(display);
    } catch (err) {
      // NotAllowedError is the candidate dismissing the picker - not worth an error banner.
      if (err instanceof DOMException && err.name === "NotAllowedError") return;
      setError("Screen sharing is unavailable in this browser.");
    }
  }, [stop]);

  useEffect(() => stop, [stop]);

  const supported = typeof navigator !== "undefined" && Boolean(navigator.mediaDevices?.getDisplayMedia);

  return { stream, error, supported, start, stop };
}
