# Hack Club Scraps Down Detector

A small Streamlit page that checks whether `scraps.hackclub.com` responds. The
target is fixed in the server code; visitors cannot enter another URL.

## Request limits

- The server makes a `GET` request with a 5-second timeout.
- The request identifies this detector and does not follow redirects to other
  hosts.
- Results, including failures, are shared across browser sessions in one server
  process for at least 60 seconds. Concurrent sessions wait for and reuse the
  same result.
- The refresh slider starts at 60 seconds and ranges up to 5 minutes. It cannot
  make checks run faster than the shared 60-second limit.
- The status area refreshes independently of the rest of the page using
  Streamlit fragments (Streamlit 1.37 or newer).
- Each server process keeps its own cache. If the service runs multiple
  replicas, each replica can make one request per minute; keep one replica for
  a single shared request schedule.
- Timeouts and connection failures show a short status message. Raw request
  exception details are not displayed to visitors.

## Run locally

```bash
python -m pip install -r requirements.txt
streamlit run main.py
```

## Tests

The status probe tests use fake clocks and mocked responses, so they do not
contact Scraps:

```bash
python -m unittest discover -v
```

## Railway

`Procfile` and `railway.json` start Streamlit on Railway's `$PORT`. No API keys
or other environment variables are required.

## Screenshot

![Scraps Down Detector](https://github.com/user-attachments/assets/fb041e2b-bb2d-4356-945b-dfca4465dc25)
