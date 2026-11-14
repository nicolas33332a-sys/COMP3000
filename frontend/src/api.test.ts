import { afterEach, describe, expect, it, vi } from "vitest";
import { ApiError, createScenario, listScenarios } from "./api";
import example from "../../contracts/scenario.example.json";

function respondWith(status: number, body: string, contentType = "application/json") {
  vi.stubGlobal(
    "fetch",
    vi.fn(async () => new Response(body, { status, headers: { "Content-Type": contentType } })),
  );
}

async function failure(call: Promise<unknown>): Promise<ApiError> {
  try {
    await call;
  } catch (error) {
    expect(error).toBeInstanceOf(ApiError);
    return error as ApiError;
  }
  throw new Error("expected the call to fail");
}

afterEach(() => vi.unstubAllGlobals());

describe("API failures become readable errors", () => {
  it("passes on the server's message and per-field problems for invalid input", async () => {
    respondWith(
      422,
      JSON.stringify({
        error: "validation_error",
        message: "The request is not valid.",
        problems: [{ field: "waypoints.0.lat", message: "Input should be less than or equal to 90" }],
      }),
    );
    const error = await failure(createScenario(example));
    expect(error.status).toBe(422);
    expect(error.code).toBe("validation_error");
    expect(error.problems).toEqual([{ field: "waypoints.0.lat", message: "Input should be less than or equal to 90" }]);
  });

  it("explains a database outage without field problems", async () => {
    respondWith(503, JSON.stringify({ error: "database_unavailable", message: "The database cannot be reached. Is it running?", problems: [] }));
    const error = await failure(listScenarios());
    expect(error.code).toBe("database_unavailable");
    expect(error.message).toBe("The database cannot be reached. Is it running?");
    expect(error.problems).toEqual([]);
  });

  it("explains an answer that is not JSON, such as the dev proxy's error page", async () => {
    respondWith(502, "<html>Bad Gateway</html>", "text/html");
    const error = await failure(listScenarios());
    expect(error.code).toBe("bad_response");
    expect(error.message).toContain("HTTP 502");
    expect(error.message).toContain("backend is running");
  });

  it("explains a server that cannot be reached at all", async () => {
    vi.stubGlobal("fetch", vi.fn(async () => Promise.reject(new TypeError("Failed to fetch"))));
    const error = await failure(listScenarios());
    expect(error.code).toBe("network");
    expect(error.message).toContain("Cannot reach the MarineScope server");
  });
});

describe("successful calls", () => {
  it("posts the scenario as JSON and returns what the server stored", async () => {
    const stored = { ...example, id: "7c0c2bed-c8cb-42e7-bad2-6701c99240c3", created_at: "2026-11-14T20:49:57Z" };
    const fetchMock = vi.fn(async () => new Response(JSON.stringify(stored), { status: 201 }));
    vi.stubGlobal("fetch", fetchMock);

    expect(await createScenario(example)).toEqual(stored);
    const [url, init] = fetchMock.mock.calls[0] as unknown as [string, RequestInit];
    expect(url).toBe("/api/scenarios");
    expect(init.method).toBe("POST");
    expect(JSON.parse(init.body as string)).toEqual(example);
  });
});
