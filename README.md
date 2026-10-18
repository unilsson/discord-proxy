# Discord Proxy Service

A small FastAPI service for sending homelab notifications to Discord through named webhooks. It keeps Discord webhook URLs out of calling applications and supports an optional channel alias in its existing API.

## Features

- FastAPI JSON API (`POST /send`) with optional `kanal` field.
- Multiple named Discord webhooks configured in `.env`.
- Configurable default channel for callers that omit `kanal`.
- Backwards compatibility with the original `DISCORD_WEBHOOK_URL` configuration and `{"text":"..."}` requests.
- OpenAPI specification and Swagger UI for interactive documentation and testing.
- Designed to run behind the internal Nginx API proxy at `api.ulnihnw.net`.

## Installation and configuration

Clone the repository and install the dependencies:

```bash
git clone https://github.com/unilsson/discord-proxy.git
cd discord-proxy
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Copy the example configuration and replace the placeholder webhook URLs with your own:

```bash
cp .env.example .env
chmod 600 .env
```

Example `.env` for multiple Discord channels:

```dotenv
DISCORD_WEBHOOKS='{"general":"https://discord.com/api/webhooks/ID1/TOKEN1","tradera-watch":"https://discord.com/api/webhooks/ID2/TOKEN2","homelab":"https://discord.com/api/webhooks/ID3/TOKEN3"}'
DISCORD_DEFAULT_CHANNEL=general
```

- `DISCORD_WEBHOOKS` is a JSON object mapping **channel aliases** to webhook URLs. Each alias can match the Discord channel name exactly (including hyphens). Aliases are case-sensitive.
- `DISCORD_DEFAULT_CHANNEL` is the alias used when an API request omits `kanal`. It must match a key in `DISCORD_WEBHOOKS`.
- Do not commit `.env` or expose webhook URLs in application logs, client code, or API responses. `.env.example` contains placeholders only.
- Restart the running service after changing `.env` (the configuration is loaded at startup).

### Compatibility with the previous configuration

An existing deployment can keep **only** its old `.env`:

```dotenv
DISCORD_WEBHOOK_URL=https://discord.com/api/webhooks/ID/TOKEN
```

Old requests without `kanal` continue to work and use that URL, without requiring any configuration migration.

You may keep `DISCORD_WEBHOOK_URL` alongside `DISCORD_WEBHOOKS` during migration. If `DISCORD_DEFAULT_CHANNEL` is configured, it takes priority for requests without `kanal`. If no named default is configured, the legacy `DISCORD_WEBHOOK_URL` is used. At least one of these fallback choices is required. An explicit `kanal` always uses a matching named webhook; an unknown alias never falls back silently.

## API endpoint

```text
POST /send
```

The JSON field `text` is required. The optional `kanal` field selects a named webhook.

**Existing request** (default channel):

```json
{
  "text": "Hello from the homelab!"
}
```

**Named channel request:**

```json
{
  "text": "A new Tradera listing was found!",
  "kanal": "tradera-watch"
}
```

A successful send returns HTTP 200 and the original response body:

```json
{"status":"skickat"}
```

An unknown `kanal` returns HTTP 400. Failed Discord deliveries return HTTP 502. Webhook requests time out after 10 seconds. Webhook URLs are never returned to clients.

### Direct local tests

```bash
# Without channel (default)
curl -X POST 'http://127.0.0.1:21961/send' \
  -H 'Content-Type: application/json' \
  -d '{"text":"Test to default channel"}'

# Named channel
curl -X POST 'http://127.0.0.1:21961/send' \
  -H 'Content-Type: application/json' \
  -d '{"text":"Test to Tradera","kanal":"tradera-watch"}'
```

To start the service directly (rather than using your existing systemd service):

```bash
uvicorn app:app --host 127.0.0.1 --port 21961
```

## Internal Nginx API proxy

In the homelab the service is normally accessed through the central internal Nginx API proxy, rather than its host address and port.

```text
http://api.ulnihnw.net/api/discord/send
```

Nginx routes `/api/discord/` to `127.0.0.1:21961` and strips the path prefix. The FastAPI app keeps `root_path="/api/discord"`, so its automatically generated OpenAPI and Swagger URLs work through the proxy.

Use the same client request URL as before:

```bash
curl -X POST 'http://api.ulnihnw.net/api/discord/send' \
  -H 'Content-Type: application/json' \
  -d '{"text":"Test via Nginx API proxy","kanal":"homelab"}'
```

Traffic flow:

```text
Client -> http://api.ulnihnw.net/api/discord/send
       -> Nginx :80
       -> http://127.0.0.1:21961/send
       -> Discord webhook selected by kanal/default
```

The internal API proxy is intentionally HTTP-only and available only on the home network. It is separate from the Nginx TLS reverse-proxy configuration used for other internal services.

## OpenAPI and Swagger UI

- Swagger UI: `http://api.ulnihnw.net/api/discord/docs`
- OpenAPI JSON: `http://api.ulnihnw.net/api/discord/openapi.json`
- Direct service URLs: `http://127.0.0.1:21961/docs` and `http://127.0.0.1:21961/openapi.json`

The `POST /send` endpoint includes optional `kanal` in the documented request schema.

## Tests

To run unit and API tests (all outgoing Discord requests are mocked):

```bash
pip install -r requirements-dev.txt
python -m unittest discover -s tests -v
```

## Design principle

Clients should use the stable internal API URL (`http://api.ulnihnw.net/api/discord/...`) rather than the physical server address or port. This lets the service move between hosts without requiring client changes. Channel aliases similarly decouple callers from their Discord webhook URLs.
