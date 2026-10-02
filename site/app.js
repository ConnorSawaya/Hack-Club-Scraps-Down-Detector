const statusPanel = document.querySelector("#status-panel");
const title = document.querySelector("#status-title");
const message = document.querySelector("#status-message");
const checkedAt = document.querySelector("#checked-at");
const statusCode = document.querySelector("#status-code");

const copyByState = {
  pending: {
    title: "Waiting for first check",
    message: "The first scheduled check has not run yet.",
  },
  operational: {
    title: "Scraps is responding",
    message: "The homepage returned HTTP 200.",
  },
  degraded: {
    title: "Scraps returned an unexpected response",
    message: "The status check will run again on the next schedule.",
  },
  unavailable: {
    title: "Scraps could not be reached",
    message: "The status check will run again on the next schedule.",
  },
};

function formatCheckTime(value) {
  if (typeof value !== "string") return null;
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return null;
  return {
    iso: date.toISOString(),
    label: `${new Intl.DateTimeFormat("en-US", {
      dateStyle: "medium",
      timeStyle: "short",
      timeZone: "UTC",
    }).format(date)} UTC`,
  };
}

function renderStatus(data) {
  const state = Object.hasOwn(copyByState, data?.state) ? data.state : "unavailable";
  const fallback = copyByState[state];
  statusPanel.dataset.state = state;
  title.textContent = fallback.title;
  message.textContent = typeof data?.message === "string" ? data.message : fallback.message;

  const time = formatCheckTime(data?.checkedAt);
  checkedAt.dateTime = time?.iso ?? "";
  checkedAt.textContent = time?.label ?? (state === "pending" ? "Waiting for first check" : "Time unavailable");

  const code = Number.isInteger(data?.statusCode) && data.statusCode >= 100 && data.statusCode <= 599
    ? data.statusCode
    : null;
  statusCode.textContent = code === null ? "No response" : `HTTP ${code}`;
}

async function refreshStatus() {
  const url = new URL("./status.json", window.location.href);
  url.searchParams.set("_", Math.floor(Date.now() / 60_000).toString());

  try {
    const response = await fetch(url, {
      cache: "no-store",
      headers: { accept: "application/json" },
    });
    if (!response.ok) throw new Error("Status document unavailable");
    const data = await response.json();
    renderStatus(data);
  } catch {
    renderStatus({
      state: "unavailable",
      message: "The latest status document could not be loaded. Try again shortly.",
    });
  }
}

void refreshStatus();
window.setInterval(refreshStatus, 60_000);
