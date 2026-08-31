import { CROSS_CITY_CITY_ALLOWLIST, type CrossCityId } from "./types";

type CitySelectorProps = {
  selectedCityId: CrossCityId;
  onSelect: (cityId: CrossCityId) => void;
};

export function CitySelector({ selectedCityId, onSelect }: CitySelectorProps) {
  return (
    <label className="hx-cc-selector" data-testid="cross-city-selector">
      <span className="hx-kicker">Focus city</span>
      <select
        aria-label="Focus city"
        value={selectedCityId}
        onChange={(event) => onSelect(event.target.value as CrossCityId)}
      >
        {CROSS_CITY_CITY_ALLOWLIST.map((city) => (
          <option key={city.id} value={city.id}>
            {city.label}
          </option>
        ))}
      </select>
    </label>
  );
}
