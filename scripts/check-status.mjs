import { mkdir, rename, writeFile } from "node:fs/promises";
import { dirname, join, resolve } from "node:path";
import { fileURLToPath } from "node:url";

export const SCRAPS_STATUS_URL = "https://scraps.hackclub.com/";
export const REQUEST_TIMEOUT_MS = 5_000;
const USER_AGENT = "HackClubScrapsStatus/1.0 (+https://github.com/ConnorSawaya/Hack-Club-Scraps-Down-Detector)";
const projectRoot = join(dirname(fileURLToPath(import.meta.url)), "..");

function record(state, reason, checkedAt, statusCode, message) {
  return { state, reason, checkedAt, statusCode, message };
}

export async function probeStatus({ fetchImpl = globalThis.fetch, now = () => new Date() } = {}) {
  const checkedAt = now().toISOString();
  try {
    const response = await fetchImpl(SCRAPS_STATUS_URL, {
      method: "GET",
      redirect: "manual",
      cache: "no-store",
      headers: { "user-agent": USER_AGENT },
      signal: AbortSignal.timeout(REQUEST_TIMEOUT_MS),
    });

    if (response?.body && typeof response.body.cancel === "function") {
      try {
        await response.body.cancel();
      } catch {
        // The status headers are enough; a body read is unnecessary.
      }
    }

    const code = response?.status;
    if (!Number.isInteger(code) || code < 100 || code > 599) {
      return record("unavailable", "invalid_response", checkedAt, null, "Scraps returned an unreadable response.");
    }
    if (code === 200) {
      return record("operational", "http_200", checkedAt, code, "The homepage returned HTTP 200.");
    }
    if (code >= 300 && code < 400) {
      return record("degraded", "redirect", checkedAt, code, "Scraps redirected the status request; the redirect was not followed.");
    }
    return record("degraded", "http", checkedAt, code, `Scraps returned HTTP ${code}.`);
  } catch (error) {
    const isTimeout = error?.name === "TimeoutError" || error?.name === "AbortError";
    return record(
      "unavailable",
      isTimeout ? "timeout" : "network",
      checkedAt,
      null,
      isTimeout
        ? `The status request timed out after ${REQUEST_TIMEOUT_MS / 1_000} seconds.`
        : "Scraps could not be reached. It will be checked again on the next schedule.",
    );
  }
}

export async function writeStatusSnapshot({
  fetchImpl = globalThis.fetch,
  now = () => new Date(),
  outputPath = join(projectRoot, "dist", "status.json"),
} = {}) {
  const outputDirectory = dirname(outputPath);
  const temporaryPath = join(outputDirectory, ".status.json.tmp");
  await mkdir(outputDirectory, { recursive: true });
  const status = await probeStatus({ fetchImpl, now });
  await writeFile(temporaryPath, `${JSON.stringify(status, null, 2)}\n`, "utf8");
  await rename(temporaryPath, outputPath);
  console.log(`Wrote the sanitized status snapshot (${status.state}).`);
  return status;
}

const scriptPath = fileURLToPath(import.meta.url);
if (process.argv[1] && resolve(process.argv[1]) === scriptPath) {
  await writeStatusSnapshot();
}
