import { readdirSync, readFileSync } from "node:fs";
import { join } from "node:path";

const assetsDir = join(process.cwd(), "dist", "assets");
const cssFiles = readdirSync(assetsDir).filter((file) => file.endsWith(".css"));

if (cssFiles.length === 0) {
  throw new Error("No CSS assets were emitted in dist/assets.");
}

const css = cssFiles.map((file) => readFileSync(join(assetsDir, file), "utf8")).join("\n");

const forbiddenDirectives = ["@tailwind", "@apply"];
const leakedDirective = forbiddenDirectives.find((directive) => css.includes(directive));

if (leakedDirective) {
  throw new Error(`Tailwind was not compiled: found raw ${leakedDirective} in generated CSS.`);
}

const requiredSelectors = [".flex", ".min-h-screen", ".bg-sidebar", ".text-primary"];
const missingSelector = requiredSelectors.find((selector) => !css.includes(selector));

if (missingSelector) {
  throw new Error(`Generated CSS is missing expected Tailwind selector ${missingSelector}.`);
}

console.log(`CSS build verified (${cssFiles.join(", ")}).`);
