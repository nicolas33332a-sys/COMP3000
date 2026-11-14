// The scenario form's state and its conversion to the API contract.
//
// Form inputs hold text. The draft keeps that text exactly as typed, and
// draftToInput converts it once, at submit time. The server stays the judge of
// what is valid: the browser does not repeat the rules, it shows the server's
// answer next to the matching input.

import type { Problem } from "./api";
import type { DataPeriod, RegionBounds, Scenario, ScenarioInput } from "./scenario";

export interface WaypointDraft {
  lon: string;
  lat: string;
}

export interface ScenarioDraft {
  name: string;
  west: string;
  south: string;
  east: string;
  north: string;
  start_date: string;
  end_date: string;
  vessel_name: string;
  speed_knots: string;
  /** Value of a datetime-local input, read as UTC: "2024-06-01T06:00". */
  departure: string;
  interval_minutes: string;
  noise_std_c: string;
  random_seed: string;
  waypoints: WaypointDraft[];
}

/** A new draft covering all the available reference data, with no route yet. */
export function emptyDraft(available?: { region: RegionBounds; data_period: DataPeriod }): ScenarioDraft {
  return {
    name: "",
    west: available ? String(available.region.west) : "",
    south: available ? String(available.region.south) : "",
    east: available ? String(available.region.east) : "",
    north: available ? String(available.region.north) : "",
    start_date: available?.data_period.start_date ?? "",
    end_date: available?.data_period.end_date ?? "",
    vessel_name: "",
    speed_knots: "8",
    departure: available ? `${available.data_period.start_date}T06:00` : "",
    interval_minutes: "60",
    noise_std_c: "0",
    random_seed: "0",
    waypoints: [],
  };
}

/** Fill the form from an existing scenario (used by the "example" button). */
export function draftFromInput(input: ScenarioInput): ScenarioDraft {
  return {
    name: input.name,
    west: String(input.region.west),
    south: String(input.region.south),
    east: String(input.region.east),
    north: String(input.region.north),
    start_date: input.data_period.start_date,
    end_date: input.data_period.end_date,
    vessel_name: input.vessel.name,
    speed_knots: String(input.vessel.speed_knots),
    departure: utcTimestampToLocalInput(input.vessel.departure_time),
    interval_minutes: String(input.sampling.interval_minutes),
    noise_std_c: String(input.sampling.noise_std_c ?? 0),
    random_seed: String(input.sampling.random_seed ?? 0),
    waypoints: input.waypoints.map((p) => ({ lon: String(p.lon), lat: String(p.lat) })),
  };
}

/** Blank or non-numeric text becomes NaN, which is sent as null and rejected by the server. */
export function toNumber(text: string): number {
  return text.trim() === "" ? Number.NaN : Number(text);
}

/** "2024-06-01T06:00" (form, UTC) -> "2024-06-01T06:00:00Z" (API). */
export function localInputToUtcTimestamp(value: string): string {
  if (value === "") return "";
  return value.length === 16 ? `${value}:00Z` : `${value}Z`;
}

/** "2024-06-01T06:00:00Z" (API) -> "2024-06-01T06:00" (form, UTC). */
export function utcTimestampToLocalInput(value: string): string {
  return value.slice(0, 16);
}

export function draftToInput(draft: ScenarioDraft): ScenarioInput {
  return {
    name: draft.name,
    region: {
      west: toNumber(draft.west),
      south: toNumber(draft.south),
      east: toNumber(draft.east),
      north: toNumber(draft.north),
    },
    data_period: { start_date: draft.start_date, end_date: draft.end_date },
    vessel: {
      name: draft.vessel_name,
      speed_knots: toNumber(draft.speed_knots),
      departure_time: localInputToUtcTimestamp(draft.departure),
    },
    // Waypoints keep the order of the rows on screen; each is named lon/lat, never positional.
    waypoints: draft.waypoints.map((p) => ({ lon: toNumber(p.lon), lat: toNumber(p.lat) })),
    sampling: {
      interval_minutes: toNumber(draft.interval_minutes),
      noise_std_c: toNumber(draft.noise_std_c),
      random_seed: toNumber(draft.random_seed),
    },
  };
}

const FIELD_LABELS: Record<string, string> = {
  scenario: "Scenario",
  name: "Scenario name",
  region: "Region",
  "region.west": "Region west",
  "region.south": "Region south",
  "region.east": "Region east",
  "region.north": "Region north",
  data_period: "Data period",
  "data_period.start_date": "Data period start",
  "data_period.end_date": "Data period end",
  "vessel.name": "Vessel name",
  "vessel.speed_knots": "Vessel speed",
  "vessel.departure_time": "Departure time",
  waypoints: "Waypoints",
  "sampling.interval_minutes": "Sampling interval",
  "sampling.noise_std_c": "Sensor noise",
  "sampling.random_seed": "Random seed",
};

/** "waypoints.2.lat" -> "Waypoint 3 latitude"; unknown paths are shown as they are. */
export function fieldLabel(field: string): string {
  const waypoint = /^waypoints\.(\d+)\.(lon|lat)$/.exec(field);
  if (waypoint) {
    return `Waypoint ${Number(waypoint[1]) + 1} ${waypoint[2] === "lon" ? "longitude" : "latitude"}`;
  }
  return FIELD_LABELS[field] ?? field;
}

/** The first message for each field path, for showing next to the matching input. */
export function problemsByField(problems: Problem[]): Record<string, string> {
  const byField: Record<string, string> = {};
  for (const problem of problems) {
    if (!(problem.field in byField)) byField[problem.field] = problem.message;
  }
  return byField;
}

/** The dates of `available` that fall inside a scenario's data period. */
export function datesInPeriod(available: string[], scenario: Pick<Scenario, "data_period"> | null): string[] {
  if (!scenario) return available;
  const { start_date, end_date } = scenario.data_period;
  // ISO dates compare correctly as text.
  return available.filter((day) => day >= start_date && day <= end_date);
}
