import { AREA_IDENTITY_REGISTRY } from "./generatedRegistry";

export type AreaIdentityV1 = {
  area_id: string;
  city_id: string;
  geoid: string;
  display_name: string;
  short_name: string;
  secondary_label: string;
  name_source: string;
  name_source_version: string;
  name_confidence: string;
  geometry_version: string | null;
  fallback_level: number;
  internal_index: number;
  geography_kind: string;
  method_detail: string;
};

export type AreaIdentityPackage = {
  schema: string;
  city_id: string;
  city_label: string;
  geography_kind: string;
  areas: readonly AreaIdentityV1[];
};

const PHOENIX_LOCAL = AREA_IDENTITY_REGISTRY["phoenix-local"] as AreaIdentityPackage;
const CROSS_CITY_PACKAGES: Record<string, AreaIdentityPackage> = {
  "phoenix-az": AREA_IDENTITY_REGISTRY["cross-city/phoenix"] as AreaIdentityPackage,
  "las-vegas-nv": AREA_IDENTITY_REGISTRY["cross-city/las_vegas"] as AreaIdentityPackage,
  "tucson-az": AREA_IDENTITY_REGISTRY["cross-city/tucson"] as AreaIdentityPackage,
  "los-angeles-ca": AREA_IDENTITY_REGISTRY["cross-city/los_angeles"] as AreaIdentityPackage,
};

function indexByGeoid(pkg: AreaIdentityPackage): Map<string, AreaIdentityV1> {
  return new Map(pkg.areas.map((row) => [row.geoid, row]));
}

const PHOENIX_LOCAL_BY_GEOID = indexByGeoid(PHOENIX_LOCAL);
const CROSS_CITY_BY_CITY: Record<string, Map<string, AreaIdentityV1>> = Object.fromEntries(
  Object.entries(CROSS_CITY_PACKAGES).map(([cityId, pkg]) => [cityId, indexByGeoid(pkg)]),
);

/** Format Census tract short name from an 11-digit GEOID. */
export function tractShortNameFromGeoid(geoid: string): string {
  const padded = geoid.padStart(11, "0");
  const tractce = padded.slice(-6);
  const suffix = tractce.slice(-2);
  const prefix = tractce.slice(0, -2).replace(/^0+/, "") || "0";
  return `${prefix}.${suffix}`;
}

export function tractDisplayNameFromGeoid(geoid: string): string {
  return `Census Tract ${tractShortNameFromGeoid(geoid)}`;
}

export function resolvePhoenixLocalIdentity(
  geoid: string | null | undefined,
): AreaIdentityV1 | null {
  if (!geoid) {
    return null;
  }
  return PHOENIX_LOCAL_BY_GEOID.get(geoid) ?? null;
}

export function resolveCrossCityIdentity(
  cityId: string,
  geoid: string | null | undefined,
): AreaIdentityV1 | null {
  if (!geoid) {
    return null;
  }
  return CROSS_CITY_BY_CITY[cityId]?.get(geoid) ?? null;
}

export function phoenixLocalDisplayName(geoid: string | null | undefined): string | null {
  const hit = resolvePhoenixLocalIdentity(geoid);
  if (hit) {
    return hit.display_name;
  }
  if (!geoid) {
    return null;
  }
  return tractDisplayNameFromGeoid(geoid);
}

export function phoenixLocalSecondaryLabel(geoid: string | null | undefined): string | null {
  return resolvePhoenixLocalIdentity(geoid)?.secondary_label ?? null;
}

export function crossCityDisplayName(cityId: string, geoid: string): string {
  return resolveCrossCityIdentity(cityId, geoid)?.display_name ?? tractDisplayNameFromGeoid(geoid);
}

export function crossCitySecondaryLabel(cityId: string, geoid: string): string | null {
  return resolveCrossCityIdentity(cityId, geoid)?.secondary_label ?? null;
}

export function assertAreaIdentityQa(pkg: AreaIdentityPackage): string[] {
  const errors: string[] = [];
  const labels = new Map<string, string>();
  for (const row of pkg.areas) {
    if (!row.display_name?.trim()) {
      errors.push(`${row.area_id}: blank display_name`);
    }
    if (/^(Analysis|Comparison) Area \d+$/i.test(row.display_name)) {
      errors.push(`${row.area_id}: generic numbered primary label`);
    }
    if (row.display_name.includes("undefined")) {
      errors.push(`${row.area_id}: undefined in display_name`);
    }
    const prior = labels.get(row.display_name);
    if (prior) {
      errors.push(`duplicate dropdown label "${row.display_name}" (${prior}, ${row.area_id})`);
    }
    labels.set(row.display_name, row.area_id);
    if (!row.city_id || row.city_id !== pkg.city_id) {
      errors.push(`${row.area_id}: wrong-city city_id`);
    }
  }
  return errors;
}

export function allIdentityPackages(): AreaIdentityPackage[] {
  return [PHOENIX_LOCAL, ...Object.values(CROSS_CITY_PACKAGES)];
}
