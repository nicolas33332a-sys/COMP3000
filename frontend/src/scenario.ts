// TypeScript mirror of the scenario contract.
//
// Source of truth: backend/marinescope/scenario.py
// Generated schema: docs/contracts/scenario.schema.json
// Explanation:      docs/contracts/scenario-contract.md
//
// Conventions: WGS84 decimal degrees, lon -180..180, lat -90..90. Fields are
// named lon/lat; when a bare pair is needed (GeoJSON, MapLibre) the order is
// [lon, lat]. Dates are "YYYY-MM-DD" UTC days, inclusive. Timestamps are
// ISO 8601 strings in UTC. Units are in the field names.

export interface Waypoint {
  lon: number;
  lat: number;
}

export interface RegionBounds {
  west: number;
  south: number;
  east: number;
  north: number;
}

export interface DataPeriod {
  /** "YYYY-MM-DD", UTC day, inclusive */
  start_date: string;
  /** "YYYY-MM-DD", UTC day, inclusive */
  end_date: string;
}

export interface VesselSettings {
  name: string;
  speed_knots: number;
  /** ISO 8601 with offset, e.g. "2024-06-01T06:00:00Z" */
  departure_time: string;
}

export interface SamplingSettings {
  interval_minutes: number;
  /** Standard deviation of simulated sensor noise, degrees Celsius. Server default 0. */
  noise_std_c?: number;
  /** Server default 0. */
  random_seed?: number;
}

/** What the browser sends to create a scenario. */
export interface ScenarioInput {
  name: string;
  region: RegionBounds;
  data_period: DataPeriod;
  vessel: VesselSettings;
  /** Route in visiting order; 2 to 100 points, all inside `region`. */
  waypoints: Waypoint[];
  sampling: SamplingSettings;
}

/** A stored scenario as returned by the server (from MS-04). */
export interface Scenario extends ScenarioInput {
  id: string;
  created_at: string;
}

/** The one place a waypoint becomes a bare pair: always [lon, lat]. */
export function toLonLat(point: Waypoint): [number, number] {
  return [point.lon, point.lat];
}
