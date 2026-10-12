import { describe, expect, it } from "vitest";

import { pickVoice, splitForSpeech } from "./speechChunks";

describe("splitForSpeech", () => {
  it("splits Arabic sentences on Arabic and Latin punctuation", () => {
    const text = "أهلاً بك سارة. حدثيني عن آخر مشروع؟ وكيف قستِ الأداء؛ بالأرقام!";
    expect(splitForSpeech(text)).toEqual(["أهلاً بك سارة.", "حدثيني عن آخر مشروع؟", "وكيف قستِ الأداء؛", "بالأرقام!"]);
  });

  it("keeps embedded English terms with their sentence", () => {
    expect(splitForSpeech("استخدمتِ Redis cache مع TTL. ممتاز.")).toEqual(["استخدمتِ Redis cache مع TTL.", "ممتاز."]);
  });

  it("hard-splits a run-on sentence without punctuation at a word boundary", () => {
    const runOn = Array.from({ length: 60 }, (_, i) => `كلمة${i}`).join(" ");
    const chunks = splitForSpeech(runOn, 100);
    expect(chunks.length).toBeGreaterThan(1);
    expect(chunks.every((c) => c.length <= 100)).toBe(true);
    expect(chunks.join(" ")).toBe(runOn);
  });

  it("returns nothing for blank text", () => {
    expect(splitForSpeech("   \n ")).toEqual([]);
  });
});

describe("pickVoice", () => {
  const voice = (name: string, lang: string) => ({ name, lang }) as SpeechSynthesisVoice;
  const voices = [voice("David", "en-US"), voice("Naayf", "ar-SA"), voice("Hoda", "ar-EG")];

  it("prefers the exact locale", () => {
    expect(pickVoice(voices, "ar-EG")?.name).toBe("Hoda");
  });

  it("falls back to the same language in another locale", () => {
    expect(pickVoice(voices, "ar-JO")?.name).toBe("Naayf");
  });

  it("returns null when the language has no voice", () => {
    expect(pickVoice(voices, "fr-FR")).toBeNull();
  });
});
