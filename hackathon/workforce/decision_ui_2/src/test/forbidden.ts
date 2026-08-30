import { FORBIDDEN_PUBLIC } from "@/ia/copy";

export function assertNoForbidden(text: string): void {
  const haystack = text.toLowerCase();
  for (const token of FORBIDDEN_PUBLIC) {
    if (haystack.includes(token.toLowerCase())) {
      throw new Error(`Forbidden public token found: ${token}`);
    }
  }
}

export function collectPublishedCopy(values: readonly unknown[]): string {
  return values
    .flatMap((value) => flatten(value))
    .join("\n");
}

function flatten(value: unknown): string[] {
  if (typeof value === "string") {
    return [value];
  }
  if (Array.isArray(value)) {
    return value.flatMap((item) => flatten(item));
  }
  if (value && typeof value === "object") {
    return Object.entries(value).flatMap(([key, item]) => {
      if (key === "FORBIDDEN_PUBLIC") {
        return [];
      }
      return flatten(item);
    });
  }
  return [];
}
