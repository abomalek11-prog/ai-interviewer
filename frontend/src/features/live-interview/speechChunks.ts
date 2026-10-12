/**
 * Split a reply into short pieces for SpeechSynthesis.
 *
 * Chrome silently stops a single long utterance after ~15s, so a 3-4 sentence answer
 * read as one utterance gets cut off mid-way. Queuing sentence-sized pieces avoids that.
 * Handles Latin and Arabic punctuation (؟ ؛ ،), and hard-splits any run-on sentence
 * that has no punctuation at all.
 */
export function splitForSpeech(text: string, maxLength = 180): string[] {
  const sentences = text
    .replace(/\s+/g, " ")
    .trim()
    .split(/(?<=[.!?؟؛…])\s+/u)
    .map((s) => s.trim())
    .filter(Boolean);

  const chunks: string[] = [];
  for (const sentence of sentences) {
    if (sentence.length <= maxLength) {
      chunks.push(sentence);
      continue;
    }
    // Run-on sentence: break at the last comma or space before the limit.
    let rest = sentence;
    while (rest.length > maxLength) {
      const window = rest.slice(0, maxLength);
      const cut = Math.max(window.lastIndexOf("،"), window.lastIndexOf(","), window.lastIndexOf(" "));
      const at = cut > maxLength / 3 ? cut + 1 : maxLength;
      chunks.push(rest.slice(0, at).trim());
      rest = rest.slice(at).trim();
    }
    if (rest) chunks.push(rest);
  }
  return chunks;
}

// Neural voices ("Microsoft Hamed Online (Natural)" in Edge, "Google ..." in Chrome) sound
// far better than the legacy OS voices such as "Microsoft Naayf", which are robotic.
const NATURAL_VOICE = /natural|neural|online|google/i;

/**
 * Best voice for a BCP-47 tag. Language fit first (exact locale, then same language in
 * another locale), and within each a neural voice beats a legacy one - a natural ar-EG
 * voice is preferred over a robotic ar-SA one.
 */
export function pickVoice(voices: SpeechSynthesisVoice[], lang: string): SpeechSynthesisVoice | null {
  const wanted = lang.toLowerCase();
  const base = wanted.split("-")[0];
  const exact = voices.filter((v) => v.lang.toLowerCase().replace("_", "-") === wanted);
  const sameLanguage = voices.filter((v) => v.lang.toLowerCase().split(/[-_]/)[0] === base);
  const natural = (list: SpeechSynthesisVoice[]) => list.find((v) => NATURAL_VOICE.test(v.name));
  return natural(exact) ?? natural(sameLanguage) ?? exact[0] ?? sameLanguage[0] ?? null;
}
