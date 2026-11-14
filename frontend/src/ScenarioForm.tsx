import type { FormEvent } from "react";
import type { Problem } from "./api";
import { fieldLabel, problemsByField } from "./form";
import type { ScenarioDraft } from "./form";

interface Props {
  draft: ScenarioDraft;
  onChange: (draft: ScenarioDraft) => void;
  onSubmit: () => void;
  onUseExample: () => void;
  saving: boolean;
  /** Problems the server reported for the last attempt. */
  problems: Problem[];
  /** A failure that is not about the input (server down, database down). */
  failure: string | null;
}

export function ScenarioForm({ draft, onChange, onSubmit, onUseExample, saving, problems, failure }: Props) {
  const errors = problemsByField(problems);
  const set = (patch: Partial<ScenarioDraft>) => onChange({ ...draft, ...patch });

  const setWaypoint = (index: number, key: "lon" | "lat", value: string) =>
    set({ waypoints: draft.waypoints.map((point, i) => (i === index ? { ...point, [key]: value } : point)) });
  const moveWaypoint = (index: number, by: -1 | 1) => {
    const next = [...draft.waypoints];
    [next[index], next[index + by]] = [next[index + by], next[index]];
    set({ waypoints: next });
  };

  const submit = (event: FormEvent) => {
    event.preventDefault();
    onSubmit();
  };

  /** A labelled input wired to one contract field path, with the server's message beneath it. */
  const field = (
    path: string,
    label: string,
    key: Exclude<keyof ScenarioDraft, "waypoints">,
    extra: { type?: string; hint?: string; inputMode?: "decimal" | "numeric" } = {},
  ) => (
    <label className="field">
      <span>{label}</span>
      <input
        name={path}
        type={extra.type ?? "text"}
        inputMode={extra.inputMode}
        value={draft[key]}
        onChange={(event) => set({ [key]: event.target.value })}
        aria-invalid={path in errors}
        aria-describedby={path in errors ? `error-${path}` : undefined}
      />
      {extra.hint && <small>{extra.hint}</small>}
      {path in errors && (
        <small className="field-error" id={`error-${path}`}>
          {errors[path]}
        </small>
      )}
    </label>
  );

  return (
    // noValidate: the server decides what is valid, and its messages are shown here.
    <form onSubmit={submit} noValidate aria-label="New scenario">
      {failure && (
        <div className="alert" role="alert">
          <strong>Not saved.</strong> {failure}
        </div>
      )}
      {problems.length > 0 && (
        <div className="alert" role="alert">
          <strong>Not saved. Please correct:</strong>
          <ul>
            {problems.map((problem, index) => (
              <li key={index}>
                {fieldLabel(problem.field)}: {problem.message}
              </li>
            ))}
          </ul>
        </div>
      )}

      {field("name", "Scenario name", "name")}

      <fieldset>
        <legend>Region (degrees, WGS84)</legend>
        <div className="grid-4">
          {field("region.west", "West", "west", { inputMode: "decimal" })}
          {field("region.south", "South", "south", { inputMode: "decimal" })}
          {field("region.east", "East", "east", { inputMode: "decimal" })}
          {field("region.north", "North", "north", { inputMode: "decimal" })}
        </div>
        <small>Longitude −180 to 180 (west is negative); latitude −90 to 90.</small>
      </fieldset>

      <fieldset>
        <legend>Historical data period (UTC days, inclusive)</legend>
        <div className="grid-2">
          {field("data_period.start_date", "First day", "start_date", { type: "date" })}
          {field("data_period.end_date", "Last day", "end_date", { type: "date" })}
        </div>
      </fieldset>

      <fieldset>
        <legend>Vessel</legend>
        {field("vessel.name", "Vessel name", "vessel_name")}
        <div className="grid-2">
          {field("vessel.speed_knots", "Speed (knots)", "speed_knots", { inputMode: "decimal" })}
          {field("vessel.departure_time", "Departure (UTC)", "departure", { type: "datetime-local" })}
        </div>
      </fieldset>

      <fieldset>
        <legend>Sampling</legend>
        <div className="grid-3">
          {field("sampling.interval_minutes", "Interval (minutes)", "interval_minutes", { inputMode: "numeric" })}
          {field("sampling.noise_std_c", "Sensor noise (°C)", "noise_std_c", { inputMode: "decimal" })}
          {field("sampling.random_seed", "Random seed", "random_seed", { inputMode: "numeric" })}
        </div>
      </fieldset>

      <fieldset>
        <legend>Waypoints, in visiting order</legend>
        <small>Click the map to add a point, or type coordinates. At least two are needed.</small>
        {"waypoints" in errors && <small className="field-error">{errors.waypoints}</small>}
        <table className="waypoints">
          <thead>
            <tr>
              <th scope="col">#</th>
              <th scope="col">Longitude (°E)</th>
              <th scope="col">Latitude (°N)</th>
              <th scope="col">
                <span className="visually-hidden">Actions</span>
              </th>
            </tr>
          </thead>
          <tbody>
            {draft.waypoints.map((point, index) => (
              <tr key={index}>
                <th scope="row">{index + 1}</th>
                {(["lon", "lat"] as const).map((key) => {
                  const path = `waypoints.${index}.${key}`;
                  return (
                    <td key={key}>
                      <input
                        name={path}
                        inputMode="decimal"
                        aria-label={fieldLabel(path)}
                        aria-invalid={path in errors}
                        title={errors[path]}
                        value={point[key]}
                        onChange={(event) => setWaypoint(index, key, event.target.value)}
                      />
                      {path in errors && <small className="field-error">{errors[path]}</small>}
                    </td>
                  );
                })}
                <td className="row-actions">
                  <button type="button" onClick={() => moveWaypoint(index, -1)} disabled={index === 0} aria-label={`Move waypoint ${index + 1} earlier`}>
                    ↑
                  </button>
                  <button type="button" onClick={() => moveWaypoint(index, 1)} disabled={index === draft.waypoints.length - 1} aria-label={`Move waypoint ${index + 1} later`}>
                    ↓
                  </button>
                  <button type="button" onClick={() => set({ waypoints: draft.waypoints.filter((_, i) => i !== index) })} aria-label={`Remove waypoint ${index + 1}`}>
                    ✕
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
        <button type="button" onClick={() => set({ waypoints: [...draft.waypoints, { lon: "", lat: "" }] })}>
          Add waypoint row
        </button>
      </fieldset>

      <div className="form-actions">
        <button type="submit" className="primary" disabled={saving}>
          {saving ? "Saving…" : "Save scenario"}
        </button>
        <button type="button" onClick={onUseExample}>
          Fill with example
        </button>
      </div>
    </form>
  );
}
