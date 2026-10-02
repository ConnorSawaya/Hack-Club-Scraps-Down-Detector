import assert from "node:assert/strict";
import { mkdtemp, readFile, rm } from "node:fs/promises";
import test from "node:test";
import { tmpdir } from "node:os";
import { join } from "node:path";
import {
  probeStatus,
  REQUEST_TIMEOUT_MS,
  SCRAPS_STATUS_URL,
  writeStatusSnapshot,
} from "../scripts/check-status.mjs";

const fixedTime = new Date("2026-10-01T12:34:56.000Z");

function fakeResponse(status) {
  return new Response(null, { status });
}

function captureFetch(handler) {
  const calls = [];
  return {
    calls,
    fetchImpl: async (url, options) => {
      calls.push({ url, options });
      return handler(url, options);
    },
  };
}

function assertSingleFixedGet(calls) {
  assert.equal(calls.length, 1, "one upstream request is allowed per probe");
  assert.equal(calls[0].url, SCRAPS_STATUS_URL);
  assert.equal(calls[0].options.method, "GET");
  assert.equal(calls[0].options.redirect, "manual");
  assert.equal(calls[0].options.cache, "no-store");
  assert.ok(calls[0].options.signal instanceof AbortSignal);
  assert.equal(REQUEST_TIMEOUT_MS, 5_000);
  assert.match(calls[0].options.headers["user-agent"], /^HackClubScrapsStatus\//);
}

test("healthy HTTP 200 is reported as operational with one fixed GET", async () => {
  const fake = captureFetch(() => fakeResponse(200));
  const result = await probeStatus({ fetchImpl: fake.fetchImpl, now: () => fixedTime });

  assert.equal(result.state, "operational");
  assert.equal(result.reason, "http_200");
  assert.equal(result.statusCode, 200);
  assert.equal(result.checkedAt, fixedTime.toISOString());
  assertSingleFixedGet(fake.calls);
});

test("timeout becomes a safe unavailable result without retrying", async () => {
  const timeout = new Error("private transport detail");
  timeout.name = "TimeoutError";
  const fake = captureFetch(() => Promise.reject(timeout));
  const result = await probeStatus({ fetchImpl: fake.fetchImpl, now: () => fixedTime });

  assert.equal(result.state, "unavailable");
  assert.equal(result.reason, "timeout");
  assert.match(result.message, /timed out after 5 seconds/);
  assert.doesNotMatch(JSON.stringify(result), /private transport detail/);
  assertSingleFixedGet(fake.calls);
});

test("non-200 response becomes a degraded result and still publishes", async () => {
  const fake = captureFetch(() => fakeResponse(503));
  const result = await probeStatus({ fetchImpl: fake.fetchImpl, now: () => fixedTime });

  assert.equal(result.state, "degraded");
  assert.equal(result.reason, "http");
  assert.equal(result.statusCode, 503);
  assert.equal(result.message, "Scraps returned HTTP 503.");
  assertSingleFixedGet(fake.calls);
});

test("redirect is recorded without following its destination", async () => {
  const fake = captureFetch(() => fakeResponse(302));
  const result = await probeStatus({ fetchImpl: fake.fetchImpl, now: () => fixedTime });

  assert.equal(result.state, "degraded");
  assert.equal(result.reason, "redirect");
  assert.equal(result.statusCode, 302);
  assert.doesNotMatch(JSON.stringify(result), /location/i);
  assertSingleFixedGet(fake.calls);
});

test("connection failure is sanitized and does not retry", async () => {
  const fake = captureFetch(() => Promise.reject(new Error("sensitive hostname detail")));
  const result = await probeStatus({ fetchImpl: fake.fetchImpl, now: () => fixedTime });

  assert.equal(result.state, "unavailable");
  assert.equal(result.reason, "network");
  assert.doesNotMatch(JSON.stringify(result), /sensitive hostname detail/);
  assertSingleFixedGet(fake.calls);
});

test("invalid response metadata is unavailable after the sole request", async () => {
  const fake = captureFetch(() => ({ status: Number.NaN }));
  const result = await probeStatus({ fetchImpl: fake.fetchImpl, now: () => fixedTime });

  assert.equal(result.state, "unavailable");
  assert.equal(result.reason, "invalid_response");
  assert.equal(result.statusCode, null);
  assertSingleFixedGet(fake.calls);
});

test("timeout and HTTP error snapshots are written for Pages publication", async () => {
  const directory = await mkdtemp(join(tmpdir(), "scraps-pages-status-test-"));
  try {
    const timeout = new Error("private timeout detail");
    timeout.name = "TimeoutError";
    const timeoutFake = captureFetch(() => Promise.reject(timeout));
    const timeoutPath = join(directory, "timeout", "status.json");
    const timeoutResult = await writeStatusSnapshot({
      fetchImpl: timeoutFake.fetchImpl,
      now: () => fixedTime,
      outputPath: timeoutPath,
    });
    const timeoutDocument = JSON.parse(await readFile(timeoutPath, "utf8"));
    assert.equal(timeoutDocument.reason, "timeout");
    assert.equal(timeoutDocument.state, "unavailable");
    assert.equal(timeoutResult.state, "unavailable");
    assertSingleFixedGet(timeoutFake.calls);

    const errorFake = captureFetch(() => fakeResponse(503));
    const errorPath = join(directory, "http-error", "status.json");
    const errorResult = await writeStatusSnapshot({
      fetchImpl: errorFake.fetchImpl,
      now: () => fixedTime,
      outputPath: errorPath,
    });
    const errorDocument = JSON.parse(await readFile(errorPath, "utf8"));
    assert.equal(errorDocument.statusCode, 503);
    assert.equal(errorDocument.state, "degraded");
    assert.equal(errorResult.state, "degraded");
    assertSingleFixedGet(errorFake.calls);
  } finally {
    await rm(directory, { recursive: true, force: true });
  }
});
