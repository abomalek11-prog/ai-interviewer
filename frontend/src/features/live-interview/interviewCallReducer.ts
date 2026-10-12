export type CallState =
  | "connecting"
  | "ai_speaking"
  | "listening"
  | "candidate_speaking"
  | "processing"
  // End requested; the backend is writing the evaluation (~a minute on free models).
  | "finishing"
  | "ended"
  | "mic_error";

export interface TranscriptEntry {
  id: string;
  role: "ai" | "candidate";
  text: string;
}

export interface InterviewCallState {
  call: CallState;
  transcript: TranscriptEntry[];
  notice: string | null;
  connectionError: string | null;
  overallScore: number | null;
}

export const initialInterviewCallState: InterviewCallState = {
  call: "connecting",
  transcript: [],
  notice: null,
  connectionError: null,
  overallScore: null,
};

export type CallEvent =
  | { type: "speech_start" }
  | { type: "speech_end"; text?: string; audioBlob?: Blob }
  | { type: "vad_misfire" }
  | { type: "ai_text"; text: string }
  | { type: "ai_audio_ended" }
  | { type: "transcript"; text: string }
  | { type: "notice"; message: string }
  | { type: "end_requested" }
  | { type: "summary"; overallScore: number | null }
  | { type: "socket_error"; message: string }
  | { type: "socket_closed" }
  | { type: "mic_error"; message: string };

export interface TransitionDeps {
  /** Called exactly when a barge-in happens: candidate speech detected while the AI is still talking. */
  stopAiPlayback: () => void;
  /** Called once a candidate utterance is complete and ready to send to the backend. */
  submitTurn: (input: { text?: string; audioBlob?: Blob }) => void;
}

/**
 * Pure state-transition function for the live-interview call. No React, no DOM, no
 * network - side effects are invoked through `deps` so this is fully unit-testable by
 * passing mock functions and asserting both the returned state and which deps fired.
 */
export function transition(state: InterviewCallState, event: CallEvent, deps: TransitionDeps): InterviewCallState {
  switch (event.type) {
    case "speech_start": {
      if (state.call === "ai_speaking") {
        deps.stopAiPlayback();
        return { ...state, call: "candidate_speaking", notice: null };
      }
      if (state.call === "listening") {
        return { ...state, call: "candidate_speaking", notice: null };
      }
      // connecting / candidate_speaking / processing / ended / mic_error: ignore stray or overlapping triggers.
      return state;
    }

    case "speech_end": {
      if (state.call !== "candidate_speaking") return state;
      const hasContent = Boolean(event.text?.trim()) || Boolean(event.audioBlob && event.audioBlob.size > 0);
      if (!hasContent) {
        return { ...state, call: "listening", notice: "I didn't catch that - make sure your microphone is working and try again." };
      }
      deps.submitTurn({ text: event.text?.trim(), audioBlob: event.audioBlob });
      return { ...state, call: "processing", notice: null };
    }

    case "vad_misfire":
      // VAD decided a detected blip wasn't real speech after all; nothing changed.
      return state;

    case "ai_text":
      return {
        ...state,
        call: "ai_speaking",
        transcript: [...state.transcript, { id: `ai-${state.transcript.length}`, role: "ai", text: event.text }],
      };

    case "transcript":
      return {
        ...state,
        transcript: [...state.transcript, { id: `cand-${state.transcript.length}`, role: "candidate", text: event.text }],
      };

    case "ai_audio_ended":
      if (state.call !== "ai_speaking") return state;
      return { ...state, call: "listening" };

    case "notice":
      return {
        ...state,
        call: state.call === "ended" || state.call === "finishing" ? state.call : "listening",
        notice: event.message,
      };

    case "end_requested":
      if (state.call === "ended" || state.call === "mic_error" || state.call === "finishing") return state;
      // The interviewer stops mid-sentence; the wait for the report must not look like a freeze.
      deps.stopAiPlayback();
      return { ...state, call: "finishing", notice: null };

    case "summary":
      return { ...state, call: "ended", overallScore: event.overallScore };

    case "socket_error":
      return { ...state, connectionError: event.message };

    case "socket_closed":
      return state.call === "ended" ? state : { ...state, call: "ended" };

    case "mic_error":
      return { ...state, call: "mic_error", connectionError: event.message };

    default:
      return state;
  }
}
