// Every call the browser makes to the MarineScope API goes through this file.
//
// Failures are turned into one ApiError type with a sentence a user can read,
// whether the server answered with an error, answered with something that is
// not JSON, or could not be reached at all.

import type { DataPeriod, RegionBounds, Scenario, ScenarioInput } from "./scenario";

export interface Problem {
  /** Dotted path into the request, e.g. "waypoints.0.lat"; "scenario" for whole-scenario rules. */
  field: string;
  message: string;
}

export class ApiError extends Error {
  constructor(
    message: string,
    /** Server error code, or "network" / "bad_response" for failures before a valid answer. */
    readonly code: string,
    readonly status: number | null = null,
    readonly problems: Problem[] = [],
  ) {
    super(message);
    this.name = "ApiError";
  }
}

export interface ReferenceMetadata {
  kind: "reference";
  description: string;
  dataset: string;
  product_page: string;
  variable: string;
  long_name: string | null;
  units: string | null;
  region: RegionBounds;
  data_period: DataPeriod;
  dates: string[];
  grid: { lat_count: number; lon_count: number; cell_size_degrees: number; coordinates: string };
  value_range: { min: number; max: number };
  retrieved_at_utc: string;
}

export interface ReferenceField {
  date: string;
  units: string | null;
  /** Cell-centre latitudes, ascending. */
  lat: number[];
  /** Cell-centre longitudes, ascending, -180..180. */
  lon: number[];
  /** values[i][j] is at lat[i], lon[j]; null where the product has no value. */
  values: (number | null)[][];
  missing_count: number;
  min: number | null;
  max: number | null;
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  let response: Response;
  try {
    response = await fetch(path, init);
  } catch {
    throw new ApiError("Cannot reach the MarineScope server. Check that the backend is running.", "network");
  }

  let body: unknown;
  try {
    body = await response.json();
  } catch {
    // For example the dev proxy answering with an HTML error page when the backend is down.
    throw new ApiError(
      response.ok
        ? "The server sent an answer that could not be read."
        : `The server could not handle the request (HTTP ${response.status}). Check that the backend is running.`,
      "bad_response",
      response.status,
    );
  }

  if (!response.ok) {
    const error = body as { error?: string; message?: string; problems?: Problem[] };
    throw new ApiError(
      error.message ?? `The request failed (HTTP ${response.status}).`,
      error.error ?? "http_error",
      response.status,
      Array.isArray(error.problems) ? error.problems : [],
    );
  }
  return body as T;
}

export function listScenarios(): Promise<Scenario[]> {
  return request<Scenario[]>("/api/scenarios");
}

export function getScenario(id: string): Promise<Scenario> {
  return request<Scenario>(`/api/scenarios/${encodeURIComponent(id)}`);
}

export function createScenario(input: ScenarioInput): Promise<Scenario> {
  return request<Scenario>("/api/scenarios", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(input),
  });
}

export function getReferenceMetadata(): Promise<ReferenceMetadata> {
  return request<ReferenceMetadata>("/api/reference-data");
}

export function getReferenceField(date: string): Promise<ReferenceField> {
  return request<ReferenceField>(`/api/reference-data/sst?date=${encodeURIComponent(date)}`);
}
