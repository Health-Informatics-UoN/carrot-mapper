import { useEffect, useState } from "react";

const TYPE_MS = 75;
const ERASE_MS = 40;
const HOLD_MS = 1600;
const NEXT_MS = 360;
const START_MS = 500;

/**
 * Types out each example, holds it, erases it, then moves to the next.
 * Decorative only: it never touches the input's value.
 * Pass a stable array (e.g. a constant) so the animation doesn't restart every render.
 */
export function useTypewriterPlaceholder(examples: readonly string[]): string {
  const [text, setText] = useState("");

  useEffect(() => {
    if (examples.length === 0) return;

    let exampleIndex = 0;
    let length = 0;
    let erasing = false;
    let timer: ReturnType<typeof setTimeout>;

    const tick = () => {
      const word = examples[exampleIndex % examples.length];
      length += erasing ? -1 : 1;
      setText(word.slice(0, length));

      if (!erasing && length >= word.length) {
        erasing = true;
        timer = setTimeout(tick, HOLD_MS);
        return;
      }
      if (erasing && length <= 0) {
        erasing = false;
        exampleIndex += 1;
        timer = setTimeout(tick, NEXT_MS);
        return;
      }
      timer = setTimeout(tick, erasing ? ERASE_MS : TYPE_MS);
    };

    timer = setTimeout(tick, START_MS);
    return () => clearTimeout(timer);
  }, [examples]);

  return text;
}
