import example from "../../docs/contracts/scenario.example.json";
import type { ScenarioInput } from "./scenario";

// Compile-time check: if the shared example stops matching the TypeScript
// types, `npm run build` fails. The backend tests validate the same file.
export const exampleScenario: ScenarioInput = example;
