import { lazy, Suspense, useEffect, useState, type ReactNode } from "react";
import { gatedPlaceSearchLanding, isPlaceSearchEnabled } from "./flags";
import { placeSearchRouteFromHash } from "./hashRoute";

const PlaceSearchShell = lazy(() =>
  import("./PlaceSearchShell").then((mod) => ({ default: mod.PlaceSearchShell })),
);

type PlaceSearchMountProps = {
  fallback: ReactNode;
};

/**
 * Optional gated lazy route. Default flag OFF → `fallback` only
 * (phoenix-demo CommandCenterShell). `#/phoenix-demo` stays the
 * legacy replay and is never aliased to Census Place 0455000.
 */
export function PlaceSearchMount({ fallback }: PlaceSearchMountProps) {
  const [route, setRoute] = useState(placeSearchRouteFromHash);

  useEffect(() => {
    const onHash = () => {
      setRoute(placeSearchRouteFromHash());
    };
    window.addEventListener("hashchange", onHash);
    return () => window.removeEventListener("hashchange", onHash);
  }, []);

  if (!isPlaceSearchEnabled() || route === "phoenix-demo") {
    return fallback;
  }

  return (
    <Suspense fallback={fallback}>
      <PlaceSearchShell />
    </Suspense>
  );
}

export default PlaceSearchMount;

export { gatedPlaceSearchLanding };
