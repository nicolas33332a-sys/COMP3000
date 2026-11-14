import { useEffect, useState } from "react";
import { exampleScenario } from "./exampleScenario";
import { toLonLat } from "./scenario";

type Health =
  | { state: "loading" }
  | { state: "ok"; version: string }
  | { state: "error"; message: string };

// First-slice shell: proves the browser can reach the API through the dev
// proxy and shows the agreed example scenario. The form and map are MS-05.
export function App() {
  const [health, setHealth] = useState<Health>({ state: "loading" });

  useEffect(() => {
    fetch("/api/health")
      .then(async (response) => {
        if (!response.ok) throw new Error(`API answered with HTTP ${response.status}`);
        const body: { version: string } = await response.json();
        setHealth({ state: "ok", version: body.version });
      })
      .catch((error: unknown) =>
        setHealth({
          state: "error",
          message: error instanceof Error ? error.message : "Unknown error",
        }),
      );
  }, []);

  return (
    <main style={{ fontFamily: "system-ui, sans-serif", maxWidth: 720, margin: "2rem auto", padding: "0 1rem" }}>
      <h1>MarineScope</h1>
      <p role="status">
        {health.state === "loading" && "Checking API…"}
        {health.state === "ok" && `API reachable (version ${health.version}).`}
        {health.state === "error" &&
          `Cannot reach the API: ${health.message}. Is the backend running on port 8000?`}
      </p>
      <h2>Example scenario (contract check)</h2>
      <p>
        {exampleScenario.name} — {exampleScenario.data_period.start_date} to{" "}
        {exampleScenario.data_period.end_date} (UTC days), {exampleScenario.vessel.speed_knots} knots, a reading
        every {exampleScenario.sampling.interval_minutes} minutes.
      </p>
      <table>
        <caption>Waypoints in visiting order, shown as [lon, lat] in WGS84 degrees</caption>
        <thead>
          <tr>
            <th scope="col">#</th>
            <th scope="col">Longitude (°E)</th>
            <th scope="col">Latitude (°N)</th>
          </tr>
        </thead>
        <tbody>
          {exampleScenario.waypoints.map((point, index) => {
            const [lon, lat] = toLonLat(point);
            return (
              <tr key={index}>
                <td>{index + 1}</td>
                <td>{lon}</td>
                <td>{lat}</td>
              </tr>
            );
          })}
        </tbody>
      </table>
      <p>
        <small>No map, form or saved data yet. Those arrive with backlog items MS-04 to MS-06.</small>
      </p>
    </main>
  );
}
