import { MAX_MESSAGE_WORDS, MAX_QUESTION_WORDS, MAX_VALUES } from "./copy";
import type { ResultCardModel } from "./types";

export function wordCount(text: string): number {
  return text
    .trim()
    .split(/\s+/)
    .filter(Boolean).length;
}

export function cardFaceText(card: ResultCardModel): string {
  const valueText = card.values.map((item) => `${item.label} ${item.value}`).join(" ");
  return [card.kicker, card.title, card.question, card.stamp, card.message, valueText]
    .filter(Boolean)
    .join(" ");
}

export function assertCardDensity(card: ResultCardModel): void {
  if (wordCount(card.question) > MAX_QUESTION_WORDS) {
    throw new Error(`Question exceeds ${MAX_QUESTION_WORDS} words.`);
  }
  if (wordCount(card.message) > MAX_MESSAGE_WORDS) {
    throw new Error(`Message exceeds ${MAX_MESSAGE_WORDS} words.`);
  }
  if (card.values.length > MAX_VALUES) {
    throw new Error(`Card has more than ${MAX_VALUES} values.`);
  }
}

export function cardIsDense(card: ResultCardModel): boolean {
  return (
    wordCount(card.question) <= MAX_QUESTION_WORDS &&
    wordCount(card.message) <= MAX_MESSAGE_WORDS &&
    card.values.length <= MAX_VALUES
  );
}
