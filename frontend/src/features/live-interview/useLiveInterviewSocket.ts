import { useCallback, useEffect, useRef } from "react";

import { interviewsApi } from "@/api/endpoints";

interface LiveInterviewSocketCallbacks {
  onAiText: (text: string) => void;
  onAiAudio: (bytes: ArrayBuffer) => void;
  onTranscript: (text: string) => void;
  onSummary: (overallScore: number | null, status: string) => void;
  onNotice: (message: string) => void;
  onError: (message: string) => void;
  onOpen: () => void;
  onClose: () => void;
}

/**
 * Pure transport for the existing live-interview WebSocket protocol - unchanged wire
 * format. Knows nothing about VAD, playback, or call state; just parses frames and
 * exposes typed send helpers.
 */
export function useLiveInterviewSocket(sessionId: string | undefined, callbacks: LiveInterviewSocketCallbacks) {
  const wsRef = useRef<WebSocket | null>(null);
  const callbacksRef = useRef(callbacks);
  callbacksRef.current = callbacks;

  useEffect(() => {
    if (!sessionId) return;
    let cancelled = false;

    const ws = new WebSocket(interviewsApi.liveWsUrl(sessionId));
    ws.binaryType = "arraybuffer";
    wsRef.current = ws;

    ws.onopen = () => {
      if (!cancelled) callbacksRef.current.onOpen();
    };

    ws.onmessage = (event) => {
      if (cancelled) return;
      if (typeof event.data === "string") {
        let payload: Record<string, unknown>;
        try {
          payload = JSON.parse(event.data);
        } catch {
          return;
        }
        switch (payload.type) {
          case "ai_text":
            callbacksRef.current.onAiText(String(payload.text ?? ""));
            break;
          case "transcript":
            callbacksRef.current.onTranscript(String(payload.text ?? ""));
            break;
          case "summary":
            callbacksRef.current.onSummary(
              typeof payload.overall_score === "number" ? payload.overall_score : null,
              String(payload.status ?? ""),
            );
            break;
          case "notice":
            callbacksRef.current.onNotice(String(payload.message ?? ""));
            break;
          case "error":
            callbacksRef.current.onError(String(payload.message ?? ""));
            break;
          default:
            break;
        }
      } else {
        callbacksRef.current.onAiAudio(event.data as ArrayBuffer);
      }
    };

    ws.onerror = () => {
      if (!cancelled) callbacksRef.current.onError("Connection to the AI interviewer was lost.");
    };
    ws.onclose = () => {
      if (!cancelled) callbacksRef.current.onClose();
    };

    return () => {
      cancelled = true;
      ws.close();
      wsRef.current = null;
    };
  }, [sessionId]);

  const sendFrame = useCallback((image: string) => {
    const ws = wsRef.current;
    if (ws?.readyState === WebSocket.OPEN) ws.send(JSON.stringify({ type: "frame", image }));
  }, []);

  const sendUserText = useCallback((text: string) => {
    const ws = wsRef.current;
    if (ws?.readyState === WebSocket.OPEN) ws.send(JSON.stringify({ type: "user_text", text }));
  }, []);

  const sendAudio = useCallback((bytes: ArrayBuffer | ArrayBufferView) => {
    const ws = wsRef.current;
    if (ws?.readyState === WebSocket.OPEN) ws.send(bytes as BufferSource);
  }, []);

  const sendEnd = useCallback(() => {
    const ws = wsRef.current;
    if (ws?.readyState === WebSocket.OPEN) ws.send(JSON.stringify({ type: "end" }));
  }, []);

  const isOpen = useCallback(() => wsRef.current?.readyState === WebSocket.OPEN, []);

  return { sendFrame, sendUserText, sendAudio, sendEnd, isOpen };
}
