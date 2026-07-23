import { useCallback, useEffect, useRef } from "react";

interface UseAiAudioPlayerOptions {
  lang: string;
  onEnded: () => void;
}

/**
 * Owns AI voice output only - nothing about VAD, interview state, or the socket.
 * `stop()` is what barge-in calls: it must synchronously silence whatever is currently
 * producing sound (an <audio> element or the SpeechSynthesis queue) so an interruption
 * feels instant.
 */
export function useAiAudioPlayer({ lang, onEnded }: UseAiAudioPlayerOptions) {
  const audioRef = useRef<HTMLAudioElement | null>(null);
  const objectUrlRef = useRef<string | null>(null);
  const onEndedRef = useRef(onEnded);
  onEndedRef.current = onEnded;

  const clearAudioElement = useCallback(() => {
    if (audioRef.current) {
      audioRef.current.onended = null;
      audioRef.current.onerror = null;
      audioRef.current.pause();
      audioRef.current = null;
    }
    if (objectUrlRef.current) {
      URL.revokeObjectURL(objectUrlRef.current);
      objectUrlRef.current = null;
    }
  }, []);

  const stop = useCallback(() => {
    clearAudioElement();
    if (typeof window !== "undefined" && "speechSynthesis" in window) {
      window.speechSynthesis.cancel();
    }
  }, [clearAudioElement]);

  const speakWithBrowser = useCallback(
    (text: string) => {
      if (typeof window === "undefined" || !("speechSynthesis" in window) || !text) {
        onEndedRef.current();
        return;
      }
      window.speechSynthesis.cancel();
      const utterance = new SpeechSynthesisUtterance(text);
      utterance.lang = lang;
      utterance.onend = () => onEndedRef.current();
      utterance.onerror = () => onEndedRef.current();
      window.speechSynthesis.speak(utterance);
    },
    [lang],
  );

  const playAudioBytes = useCallback(
    (bytes: ArrayBuffer, fallbackText: string) => {
      stop();
      const blob = new Blob([bytes], { type: "audio/mpeg" });
      if (blob.size === 0) {
        speakWithBrowser(fallbackText);
        return;
      }
      const url = URL.createObjectURL(blob);
      objectUrlRef.current = url;
      const audio = new Audio(url);
      audioRef.current = audio;
      audio.onended = () => onEndedRef.current();
      audio.onerror = () => speakWithBrowser(fallbackText);
      audio.play().catch(() => speakWithBrowser(fallbackText));
    },
    [speakWithBrowser, stop],
  );

  useEffect(() => stop, [stop]);

  return { playAudioBytes, stop };
}
