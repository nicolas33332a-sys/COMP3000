import { describe, expect, it } from "vitest";
import example from "../../contracts/scenario.example.json";
import {
  datesInPeriod,
  draftFromInput,
  draftToInput,
  emptyDraft,
  fieldLabel,
  localInputToUtcTimestamp,
  problemsByField,
  utcTimestampToLocalInput,
} from "./form";
import type { ScenarioInput } from "./scenario";

const scenario: ScenarioInput = example;

describe("form <-> contract conversion", () => {
  it("round-trips the shared example without changing any value", () => {
    expect(draftToInput(draftFromInput(scenario))).toEqual(scenario);
  });

  it("keeps waypoints in on-screen order with lon and lat never swapped", () => {
    const draft = draftFromInput(scenario);
    draft.waypoints = [
      { lon: "-13.5", lat: "45.5" },
      { lon: "-6", lat: "49.5" },
    ];
    expect(draftToInput(draft).waypoints).toEqual([
      { lon: -13.5, lat: 45.5 },
      { lon: -6, lat: 49.5 },
    ]);
  });

  it("sends blank or non-numeric input as null, so the server rejects it instead of storing 0", () => {
    const draft = draftFromInput(scenario);
    draft.speed_knots = "";
    draft.west = "abc";
    const sent = JSON.parse(JSON.stringify(draftToInput(draft)));
    expect(sent.vessel.speed_knots).toBeNull();
    expect(sent.region.west).toBeNull();
  });

  it("treats the departure input as UTC", () => {
    expect(localInputToUtcTimestamp("2024-06-01T06:00")).toBe("2024-06-01T06:00:00Z");
    expect(localInputToUtcTimestamp("2024-06-01T06:00:30")).toBe("2024-06-01T06:00:30Z");
    expect(localInputToUtcTimestamp("")).toBe("");
    expect(utcTimestampToLocalInput("2024-06-01T06:00:00Z")).toBe("2024-06-01T06:00");
  });

  it("starts a new form from the available data", () => {
    const draft = emptyDraft({
      region: { west: -16, south: 44, east: -4, north: 52 },
      data_period: { start_date: "2024-06-01", end_date: "2024-06-14" },
    });
    expect([draft.west, draft.south, draft.east, draft.north]).toEqual(["-16", "44", "-4", "52"]);
    expect(draft.departure).toBe("2024-06-01T06:00");
    expect(draft.waypoints).toEqual([]);
  });
});

describe("showing server problems", () => {
  it("names fields in plain words, with waypoints counted from 1", () => {
    expect(fieldLabel("waypoints.0.lat")).toBe("Waypoint 1 latitude");
    expect(fieldLabel("waypoints.11.lon")).toBe("Waypoint 12 longitude");
    expect(fieldLabel("vessel.speed_knots")).toBe("Vessel speed");
    expect(fieldLabel("scenario")).toBe("Scenario");
    expect(fieldLabel("something.new")).toBe("something.new");
  });

  it("indexes problems by field path, keeping the first message", () => {
    expect(
      problemsByField([
        { field: "vessel.name", message: "first" },
        { field: "vessel.name", message: "second" },
        { field: "region", message: "outside" },
      ]),
    ).toEqual({ "vessel.name": "first", region: "outside" });
  });
});

describe("dates offered in the date picker", () => {
  const available = ["2024-06-01", "2024-06-02", "2024-06-03", "2024-06-04"];

  it("offers every available date when no scenario is open", () => {
    expect(datesInPeriod(available, null)).toEqual(available);
  });

  it("offers only the scenario's own period, inclusive at both ends", () => {
    expect(datesInPeriod(available, { data_period: { start_date: "2024-06-02", end_date: "2024-06-03" } })).toEqual([
      "2024-06-02",
      "2024-06-03",
    ]);
  });
});
