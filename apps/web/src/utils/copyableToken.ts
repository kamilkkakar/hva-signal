export const TOKEN_HEAD = 12;
export const TOKEN_TAIL = 10;
export const TOKEN_LIMIT = 28;

export function isLongToken(value: string, limit = TOKEN_LIMIT): boolean {
  return value.length > limit;
}

export function truncateToken(value: string, limit = TOKEN_LIMIT): string {
  if (value.length <= limit) {
    return value;
  }
  return `${value.slice(0, TOKEN_HEAD)}…${value.slice(-TOKEN_TAIL)}`;
}
