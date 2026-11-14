import { describe, expect, it } from "vitest";
import type { ReferenceField } from "./api";
import { COLOUR_RAMP, colourStops, fieldToCells, unitSymbol } from "./reference";

// Small synthetic grid (not NOAA data): 2 latitudes x 3 longitudes, one missing cell.
const field: ReferenceField = {
  date: "2024-06-01",
  units: "Celsius",
  lat: [44.125, 44.375],
  lon: [-15.875, -15.625, -15.375],
  values: [
    [0, 1, 2],
    [10, null, 12],
  ],
  missing_count: 1,
  min: 0,
  max: 12,
};

describe("temperature grid -> map cells", () => {
  const cells = fieldToCells(field, 0.25);

  it("draws one cell per value and leaves missing cells out", () => {
    expect(cells.features).toHaveLength(5);
    expect(cells.features.map((f) => f.properties.sst)).toEqual([0, 1, 2, 10, 12]);
  });

  it("puts values[i][j] at lat[i], lon[j]", () => {
    const at = (lon: number, lat: number) =>
      cells.features.find((f) => f.properties.lon === lon && f.properties.lat === lat)?.properties.sst;
    expect(at(-15.375, 44.125)).toBe(2); // row 0 (southern latitude), last column (eastern longitude)
    expect(at(-15.875, 44.375)).toBe(10); // row 1 (northern latitude), first column
    expect(at(-15.625, 44.375)).toBeUndefined(); // the missing cell
  });

  it("draws each cell as a square of the grid size around its centre, in [lon, lat] order", () => {
    const ring = cells.features[0].geometry.coordinates[0];
    expect(ring).toEqual([
      [-16, 44],
      [-15.75, 44],
      [-15.75, 44.25],
      [-16, 44.25],
      [-16, 44],
    ]);
  });
});

describe("colour scale and labels", () => {
  it("spreads the ramp evenly from min to max", () => {
    const stops = colourStops(12, 20);
    expect(stops.map(([value]) => value)).toEqual([12, 14, 16, 18, 20]);
    expect(stops.map(([, colour]) => colour)).toEqual(COLOUR_RAMP);
  });

  it("still gives increasing stops for a flat field", () => {
    const values = colourStops(15, 15).map(([value]) => value);
    expect(values).toEqual([...values].sort((a, b) => a - b));
    expect(new Set(values).size).toBe(values.length);
  });

  it("labels the source's 'Celsius' as °C and leaves other units alone", () => {
    expect(unitSymbol("Celsius")).toBe("°C");
    expect(unitSymbol("kelvin")).toBe("kelvin");
    expect(unitSymbol(null)).toBe("");
  });
});
