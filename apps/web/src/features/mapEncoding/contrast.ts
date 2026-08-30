/** WCAG 2 relative luminance and contrast. Used to lock the bake-off, not to stretch data. */

export function hexToRgb(hex: string): [number, number, number] {
  const raw = hex.replace("#", "");
  if (raw.length !== 6) {
    throw new Error(`expected #rrggbb, got ${hex}`);
  }
  return [
    Number.parseInt(raw.slice(0, 2), 16),
    Number.parseInt(raw.slice(2, 4), 16),
    Number.parseInt(raw.slice(4, 6), 16),
  ];
}

function channelToLinear(channel: number): number {
  const scaled = channel / 255;
  return scaled <= 0.04045 ? scaled / 12.92 : ((scaled + 0.055) / 1.055) ** 2.4;
}

export function relativeLuminance(hex: string): number {
  const [r, g, b] = hexToRgb(hex);
  return (
    0.2126 * channelToLinear(r) +
    0.7152 * channelToLinear(g) +
    0.0722 * channelToLinear(b)
  );
}

export function contrastRatio(a: string, b: string): number {
  const left = relativeLuminance(a);
  const right = relativeLuminance(b);
  const lighter = Math.max(left, right);
  const darker = Math.min(left, right);
  return (lighter + 0.05) / (darker + 0.05);
}

export function blendOnto(foreground: string, background: string, opacity: number): string {
  const [fr, fg, fb] = hexToRgb(foreground);
  const [br, bg, bb] = hexToRgb(background);
  const t = Math.min(1, Math.max(0, opacity));
  const backgroundChannels = [br, bg, bb] as const;
  const hex = [fr, fg, fb]
    .map((channel, index) => {
      const other = backgroundChannels[index] ?? 0;
      const mixed = Math.round(channel * t + other * (1 - t));
      return mixed.toString(16).padStart(2, "0");
    })
    .join("");
  return `#${hex}`;
}
