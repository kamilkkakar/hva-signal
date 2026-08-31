import { useEffect, useRef } from "react";

/**
 * Parent `selectedAreaId` is authoritative.
 * The map may mirror it locally, but must NOT echo selection back to the parent
 * on prop sync or callback-identity churn — only user gestures notify parent.
 */

export type SelectionNotifyReason = "user_select" | "user_clear" | "mirror_sync";

export function shouldNotifyParentSelection(reason: SelectionNotifyReason): boolean {
  return reason === "user_select" || reason === "user_clear";
}

/**
 * Resolve parent selection after a render where the map mirror may still hold a
 * stale id and the parent callback identity may have changed.
 *
 * Historical bug: outbound `useEffect(() => onChange(mapId), [onChange, mapId])`
 * re-fired on callback identity churn and wrote the stale map id back to parent
 * before the inbound `set_selected(parentId)` effect ran — visible A→B→A flicker.
 */
export function resolveAuthoritativeSelection(input: {
  parentSelectedId: string;
  mapSelectedId: string;
  callbackIdentityChanged: boolean;
}): string {
  // Authoritative rule: parent wins. Callback identity must never rewrite parent
  // from a stale map mirror.
  void input.mapSelectedId;
  void input.callbackIdentityChanged;
  return input.parentSelectedId;
}

/**
 * Controlled mirror: apply parent id into local map state without notifying parent.
 */
export function applyParentSelectionToMap(
  parentSelectedId: string | null,
): { type: "set_selected"; geoid: string | null } {
  return { type: "set_selected", geoid: parentSelectedId };
}

/**
 * Guard: only call parent when the outgoing value is a user gesture result.
 */
export function notifyParentIfUserGesture(
  reason: SelectionNotifyReason,
  geoid: string | null,
  onSelectedIdChange?: (geoid: string | null) => void,
): void {
  if (!shouldNotifyParentSelection(reason)) {
    return;
  }
  onSelectedIdChange?.(geoid);
}

/**
 * Stable subscription helper for controlled selection.
 * Keeps latest callback in a ref so identity churn cannot re-fire outbound sync.
 */
export function useStableSelectionHandler(
  onSelectedIdChange?: (geoid: string | null) => void,
): (geoid: string | null, reason: SelectionNotifyReason) => void {
  const ref = useRef(onSelectedIdChange);
  useEffect(() => {
    ref.current = onSelectedIdChange;
  }, [onSelectedIdChange]);
  return (geoid, reason) => {
    notifyParentIfUserGesture(reason, geoid, ref.current);
  };
}
