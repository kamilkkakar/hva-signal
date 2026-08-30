import { describe, expect, it } from "vitest";
import {
  FORBIDDEN_CARD_FACE,
  MAX_MESSAGE_WORDS,
  MAX_QUESTION_WORDS,
  SIGNAL_A_MESSAGE_FAILED,
  SIGNAL_A_MESSAGE_IDLE,
  SIGNAL_A_MESSAGE_NOT_PREPARED,
  SIGNAL_A_MESSAGE_SHOWN,
  SIGNAL_A_MESSAGE_WITHHELD,
  SIGNAL_A_MESSAGE_WORKING,
  SIGNAL_A_QUESTION,
  SIGNAL_B_MESSAGE,
  SIGNAL_B_QUESTION,
  publishedCardCopy,
} from "./copy";
import { wordCount } from "./density";

const CARD_MESSAGES = [
  SIGNAL_A_MESSAGE_IDLE,
  SIGNAL_A_MESSAGE_WORKING,
  SIGNAL_A_MESSAGE_SHOWN,
  SIGNAL_A_MESSAGE_WITHHELD,
  SIGNAL_A_MESSAGE_NOT_PREPARED,
  SIGNAL_A_MESSAGE_FAILED,
  SIGNAL_B_MESSAGE,
];

describe("result card copy density", () => {
  it("keeps one question and one message under the word cap", () => {
    expect(wordCount(SIGNAL_A_QUESTION)).toBeLessThanOrEqual(MAX_QUESTION_WORDS);
    expect(wordCount(SIGNAL_B_QUESTION)).toBeLessThanOrEqual(MAX_QUESTION_WORDS);
    for (const message of CARD_MESSAGES) {
      expect(wordCount(message), message).toBeLessThanOrEqual(MAX_MESSAGE_WORDS);
    }
  });

  it("does not put method tokens or 07-01 identifiers on the card face", () => {
    const face = publishedCardCopy().join(" ");
    for (const token of FORBIDDEN_CARD_FACE) {
      expect(face.toLowerCase()).not.toContain(token.toLowerCase());
    }
    expect(face).not.toMatch(/fortyguard/i);
  });
});
