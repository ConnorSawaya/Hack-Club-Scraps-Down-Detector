import { cp, mkdir, readFile } from "node:fs/promises";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const projectRoot = join(dirname(fileURLToPath(import.meta.url)), "..");
const siteDirectory = join(projectRoot, "site");
const outputDirectory = join(projectRoot, "dist");
const requiredFiles = ["index.html", "styles.css", "app.js", "favicon.svg", "status.json"];

for (const file of requiredFiles) {
  await readFile(join(siteDirectory, file));
}

const html = await readFile(join(siteDirectory, "index.html"), "utf8");
for (const asset of ["styles.css", "app.js", "favicon.svg", "status.json"]) {
  if (!html.includes(`./${asset}`) && !(asset === "status.json" && html.includes("app.js"))) {
    throw new Error(`Expected the dashboard to reference ${asset}.`);
  }
}

const fallback = JSON.parse(await readFile(join(siteDirectory, "status.json"), "utf8"));
if (fallback.state !== "pending" || fallback.checkedAt !== null) {
  throw new Error("The checked-in Pages status must remain a pending, network-free fallback.");
}

await mkdir(outputDirectory, { recursive: true });
await cp(siteDirectory, outputDirectory, { recursive: true });
console.log(`Built the static Pages artifact in ${outputDirectory}.`);
