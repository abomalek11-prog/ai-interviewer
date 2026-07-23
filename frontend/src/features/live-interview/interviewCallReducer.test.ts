import { describe, expect, it, vi } from "vitest";

import type { InterviewCallState, TransitionDeps } from "./interviewCallReducer";
import { initialInterviewCallState, transition } from "./interviewCallReducer";

function makeDeps(): TransitionDeps & { stopAiPlayback: ReturnType<typeof vi.fn>; submitTurn: ReturnType<typeof vi.fn> } {
  return { stopAiPlayback: vi.fn(), submitTurn: vi.fn() };
}

function state(overrides: Partial<InterviewCallState>): InterviewCallState {
  return { ...initialInterviewCallState, ...overrides };
}

describe("interview call transitions", () => {
  it("runs a normal turn: listening -> speech_start -> speech_end -> processing -> ai reply -> listening", () => {
    const deps = makeDeps();
    let s = state({ call: "listening" });

    s = transition(s, { type: "speech_start" }, deps);
    expect(s.call).toBe("candidate_speaking");
    expect(deps.stopAiPlayback).not.toHaveBeenCalled();

    s = transition(s, { type: "speech_end", text: "I'd use a hash map." }, deps);
    expect(s.call).toBe("processing");
    expect(deps.submitTurn).toHaveBeenCalledWith({ text: "I'd use a hash map.", audioBlob: undefined });

    s = transition(s, { type: "transcript", text: "I'd use a hash map." }, deps);
    expect(s.transcript).toEqual([{ id: "cand-0", role: "candidate", text: "I'd use a hash map." }]);

    s = transition(s, { type: "ai_text", text: "Good, what's the complexity?" }, deps);
    expect(s.call).toBe("ai_speaking");
    expect(s.transcript).toHaveLength(2);

    s = transition(s, { type: "ai_audio_ended" }, deps);
    expect(s.call).toBe("listening");
  });

  it("barges in: candidate speech during ai_speaking stops playback immediately", () => {
    const deps = makeDeps();
    const s = transition(state({ call: "ai_speaking" }), { type: "speech_start" }, deps);

    expect(deps.stopAiPlayback).toHaveBeenCalledTimes(1);
    expect(s.call).toBe("candidate_speaking");
  });

  it("brief pause mid-sentence is a VAD-internal concern, not a reducer transition (redemptionFrames keeps VAD in the same speech segment)", () => {
    // The reducer only ever sees a single speech_start/speech_end pair for a paused-then-continued
    // utterance because VAD's redemptionFrames absorbs the pause before it fires onSpeechEnd.
    const deps = makeDeps();
    let s = state({ call: "listening" });
    s = transition(s, { type: "speech_start" }, deps);
    s = transition(s, { type: "speech_end", text: "well... let me think... it's O(n)" }, deps);
    expect(s.call).toBe("processing");
    expect(deps.submitTurn).toHaveBeenCalledTimes(1);
  });

  it("ignores a VAD misfire (too-short noise blip)", () => {
    const deps = makeDeps();
    const before = state({ call: "listening" });
    const after = transition(before, { type: "vad_misfire" }, deps);
    expect(after).toBe(before);
  });

  it("ignores speech_start while already processing or candidate_speaking (overlap guard)", () => {
    const deps = makeDeps();
    for (const call of ["processing", "candidate_speaking", "connecting", "ended"] as const) {
      const s = transition(state({ call }), { type: "speech_start" }, deps);
      expect(s.call).toBe(call);
    }
    expect(deps.stopAiPlayback).not.toHaveBeenCalled();
  });

  it("treats an empty utterance as a notice and returns to listening without submitting", () => {
    const deps = makeDeps();
    const s = transition(state({ call: "candidate_speaking" }), { type: "speech_end" }, deps);
    expect(s.call).toBe("listening");
    expect(s.notice).toMatch(/didn't catch/i);
    expect(deps.submitTurn).not.toHaveBeenCalled();
  });

  it("surfaces mic permission errors as a terminal mic_error state", () => {
    const deps = makeDeps();
    const s = transition(state({ call: "connecting" }), { type: "mic_error", message: "Camera/microphone access was blocked." }, deps);
    expect(s.call).toBe("mic_error");
    expect(s.connectionError).toMatch(/blocked/i);
  });

  it("ends the interview cleanly on socket error followed by close (no stuck spinner)", () => {
    const deps = makeDeps();
    let s = state({ call: "processing" });
    s = transition(s, { type: "socket_error", message: "Connection to the AI interviewer was lost." }, deps);
    expect(s.call).toBe("processing");
    expect(s.connectionError).toBeTruthy();

    s = transition(s, { type: "socket_closed" }, deps);
    expect(s.call).toBe("ended");
  });

  it("reaches ended on summary and stays there on a subsequent close", () => {
    const deps = makeDeps();
    let s = state({ call: "processing" });
    s = transition(s, { type: "summary", overallScore: 82 }, deps);
    expect(s.call).toBe("ended");
    expect(s.overallScore).toBe(82);

    s = transition(s, { type: "socket_closed" }, deps);
    expect(s.call).toBe("ended");
  });
});
