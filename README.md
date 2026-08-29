# Discord Proxy Service

A small FastAPI service for sending notifications to a Discord channel through a Discord webhook. It is intended for internal homelab use and keeps the webhook URL outside calling applications.

## Features

- **FastAPI backend** with a small JSON API.
- **Environment-based configuration** for the Discord webhook URL.
- **OpenAPI specification** generated automatically by FastAPI.
- **Swagger UI** for interactive API documentation and testing.
- Designed to run behind the internal Nginx API proxy at `api.ulnihnw.net`.

## Installation and setup

Clone the repository and enter the directory:

```bash
git clone https://github.com/unilsson/discord-proxy.git
cd discord-proxy
```

Create a `.env` file containing the Discord webhook URL:

```env
DISCORD_WEBHOOK_URL=your_discord_webhook_url_here
```

The `.env` file must not be committed to Git. On the production server it should only be readable by the account that owns the application, for example:

```bash
chmod 600 .env
```

## API endpoint

The service exposes one application endpoint:

```text
POST /send
```

JSON body:

```json
{
  "text": "Hello from the homelab!"
}
```

`text` is required.

### Direct local test

When testing directly on the server:

```bash
curl -X POST "http://127.0.0.1:21961/send" \
  -H "Content-Type: application/json" \
  -d '{"text":"Hello from the homelab!"}'
```

## Internal Nginx API proxy

In the homelab the service is normally accessed through the central internal Nginx API proxy rather than by its host address and port.

Internal URL:

```text
http://api.ulnihnw.net/api/discord/
```

Nginx routes requests under `/api/discord/` to the local Discord service on `127.0.0.1:21961`.

The FastAPI application uses a `root_path` because it is exposed behind the Nginx path prefix:

```python
app = FastAPI(
    title="Discord Proxy",
    description="Internt API för att skicka notifieringar via Discord",
    version="1.0.0",
    root_path="/api/discord",
)
```

This allows FastAPI-generated URLs to work correctly even though Nginx removes the `/api/discord/` prefix before forwarding the request to the backend.

The normal API call from another machine on the LAN is therefore:

```bash
curl -X POST "http://api.ulnihnw.net/api/discord/send" \
  -H "Content-Type: application/json" \
  -d '{"text":"Test via Nginx API proxy"}'
```

Traffic flow:

```text
Client
  |
  v
http://api.ulnihnw.net/api/discord/send
  |
  v
Nginx :80
  |
  v
http://127.0.0.1:21961/send
  |
  v
Discord webhook
```

The internal API proxy is intentionally HTTP-only and is available only on the home network. It is separate from the Nginx TLS reverse-proxy configuration used for other internal services.

## OpenAPI and Swagger UI

FastAPI automatically generates both a machine-readable OpenAPI description and interactive Swagger documentation.

### Swagger UI

Open in a browser:

```text
http://api.ulnihnw.net/api/discord/docs
```

The Swagger interface shows the available endpoints, request schemas and response types. The `POST /send` endpoint can also be tested directly from the browser using **Try it out**.

### OpenAPI specification

The generated OpenAPI document is available at:

```text
http://api.ulnihnw.net/api/discord/openapi.json
```

Directly on the application server the corresponding FastAPI endpoints are:

```text
http://127.0.0.1:21961/docs
http://127.0.0.1:21961/openapi.json
```

## Design principle

Clients should use the stable internal API URL:

```text
http://api.ulnihnw.net/api/discord/...
```

rather than depending on the physical server address or application port. This allows the service to move to another host or port later without requiring changes in every client that uses it.
