import { useCallback, useEffect, useRef } from "react";

import { pickVoice, splitForSpeech } from "./speechChunks";

/**
 * Where the AI's voice is coming from. It matters for echo: audio played by the page
 * ("server" TTS through an <audio> element) is removed from the mic by the browser's echo
 * canceller, but SpeechSynthesis ("browser") is rendered by the OS speech engine, outside
 * the page, so the mic hears it at full volume.
 */
export type PlaybackSource = "server" | "browser";

interface UseAiAudioPlayerOptions {
  lang: string;
  onEnded: () => void;
  onPlaybackStart?: (source: PlaybackSource) => void;
  /** No installed voice for `lang`; the reply is only shown as text. */
  onVoiceUnavailable?: (lang: string) => void;
}

/**
 * Owns AI voice output only - nothing about VAD, interview state, or the socket.
 * `stop()` is what barge-in calls: it must synchronously silence whatever is currently
 * producing sound (an <audio> element or the SpeechSynthesis queue) so an interruption
 * feels instant.
 */
export function useAiAudioPlayer({ lang, onEnded, onPlaybackStart, onVoiceUnavailable }: UseAiAudioPlayerOptions) {
  const audioRef = useRef<HTMLAudioElement | null>(null);
  const objectUrlRef = useRef<string | null>(null);
  const callbacksRef = useRef({ onEnded, onPlaybackStart, onVoiceUnavailable });
  callbacksRef.current = { onEnded, onPlaybackStart, onVoiceUnavailable };
  // Bumped on every new reply and on stop(): events from an older, cancelled playback
  // (cancel() fires `onerror: interrupted` on queued utterances) must not end the new one.
  const generationRef = useRef(0);
  // Chrome garbage-collects an utterance that nothing references while it is still being
  // spoken, and then neither speaks the rest nor fires onend. Hold them until done.
  const utterancesRef = useRef<SpeechSynthesisUtterance[]>([]);

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
    generationRef.current += 1;
    clearAudioElement();
    utterancesRef.current = [];
    if (typeof window !== "undefined" && "speechSynthesis" in window) {
      window.speechSynthesis.cancel();
    }
  }, [clearAudioElement]);

  const speakWithBrowser = useCallback(
    (text: string) => {
      const generation = generationRef.current;
      const finish = () => {
        if (generation !== generationRef.current) return;
        utterancesRef.current = [];
        callbacksRef.current.onEnded();
      };

      const chunks = splitForSpeech(text);
      if (typeof window === "undefined" || !("speechSynthesis" in window) || chunks.length === 0) {
        finish();
        return;
      }

      const synth = window.speechSynthesis;
      const voice = pickVoice(synth.getVoices(), lang);
      // getVoices() is empty until the list has loaded; only report a missing voice once it has.
      if (!voice && synth.getVoices().length > 0) callbacksRef.current.onVoiceUnavailable?.(lang);

      const utterances = chunks.map((chunk, index) => {
        const utterance = new SpeechSynthesisUtterance(chunk);
        utterance.lang = voice?.lang ?? lang;
        if (voice) utterance.voice = voice;
        if (index === chunks.length - 1) utterance.onend = finish;
        // One bad chunk must not leave the call stuck in "AI speaking".
        utterance.onerror = (event) => {
          if (event.error === "interrupted" || event.error === "canceled") return;
          finish();
        };
        return utterance;
      });
      utterancesRef.current = utterances;
      callbacksRef.current.onPlaybackStart?.("browser");

      // Chrome can drop an utterance queued in the same tick as cancel(); give it a beat.
      window.setTimeout(() => {
        if (generation !== generationRef.current) return;
        utterances.forEach((utterance) => synth.speak(utterance));
      }, 60);
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
      const generation = generationRef.current;
      const url = URL.createObjectURL(blob);
      objectUrlRef.current = url;
      const audio = new Audio(url);
      audioRef.current = audio;
      audio.onended = () => {
        if (generation === generationRef.current) callbacksRef.current.onEnded();
      };
      audio.onerror = () => speakWithBrowser(fallbackText);
      audio
        .play()
        .then(() => callbacksRef.current.onPlaybackStart?.("server"))
        .catch(() => speakWithBrowser(fallbackText));
    },
    [speakWithBrowser, stop],
  );

  useEffect(() => stop, [stop]);

  return { playAudioBytes, stop };
}
