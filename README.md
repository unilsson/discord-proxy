# Discord Proxy Service

A lightweight FastAPI microservice designed to forward notifications and alerts to a Discord channel via Webhooks. Part of a local homelab notification architecture running on Linux.

## Features
* **FastAPI Backend:** Fast, asynchronous, and reliable API endpoints.
* **Environment-Based Config:** Credentials are securely managed via `.env`.
* **Systemd Integration:** Runs as a persistent background service.

## Installation & Setup

1. Clone the repository and navigate into the folder:
   ```bash
   git clone https://github.com/YOUR_USERNAME/discord-proxy.git
   cd discord-proxy
   ```

2. Create a `.env` file based on the example:
   ```env
   DISCORD_WEBHOOK_URL=your_discord_webhook_url_here
   ```

3. Install dependencies and run using Uvicorn or via your systemd service.

## API Usage

Send a POST request to `/send`:

```bash
curl -X POST "http://127.0.0.1:21961/send" \
     -H "Content-Type: application/json" \
     -d '{"text": "Hello from the homelab!"}'
     