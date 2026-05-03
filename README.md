# Drssed — API

Backend REST API for **Drssed**, a personal wardrobe management app that digitizes clothing and outfits using automated image processing and categorization.

> This repository contains the server-side implementation. The iOS frontend is maintained separately: [drssed-ios](https://github.com/davidriegel/drssed-ios)

---

## Features

- **User management** — registration, login, JWT-based authentication
- **Wardrobe management** — create, read, update and delete clothing items per user
- **Outfit management** — combine items into outfits, store and retrieve them
- **Image processing** — background removal and automated categorization of clothing images
- **Category system** — structured data model for clothing types, colors and tags

---

## Getting Started

### Prerequisites
- Docker
- Docker Compose

### Installation

Clone the repository:

```bash
git clone https://github.com/davidriegel/drssed-api.git
cd drssed-api
```

Configure environment variables:

Create a `.env` file in the root directory based on the provided `.env.example`:

```bash
cp .env.example .env
```

```env
API_BASE_URL=http://localhost:8000

DATABASE_HOST=mysql
DATABASE_PORT=3306
DATABASE_NAME=DATABASE_NAME
DATABASE_ROOT_PASSWORD=DATABASE_ROOT_PASSWORD
DATABASE_USERNAME=DATABASE_USERNAME
DATABASE_PASSWORD=DATABASE_PASSWORD

DISABLE_SCHEDULER=False

CLEANUP_INACTIVE_DAYS=90
CLEANUP_MAX_DELETE=100

SECRET_TOKEN_KEY=SECRET_KEY_VALUE_FOR_JWT_AUTHENTICATION

RATELIMITER_ENABLED=True
REDIS_URI=redis://redis:6379

FLASK_ENV=development # 'development' or 'production'
LOG_LEVEL=INFO
```

Start the application using Docker Compose:

```bash
docker-compose up -d
```

The API will be accessible at `http://localhost:8000`.

---

## Tech Stack

| Layer | Technology |
|---|---|
| Language | Python 3.12 |
| Framework | Flask |
| Database | MySQL |
| Cache & Rate Limiting | Redis |
| Auth | JWT |
| Server | Gunicorn |
| Containerization | Docker |

---

## Monitoring (Optional)

For production deployments, structured logging and real-time monitoring are available via [drssed-monitoring](https://github.com/davidriegel/drssed-monitoring).

### Enable Production Logging

Set `FLASK_ENV=production` in your `.env` file to enable JSON-formatted logs:

```env
FLASK_ENV=production
LOG_LEVEL=INFO
```

In production mode, the API automatically outputs structured logs with request details, response times, error tracking, and performance metrics.

### Monitoring Stack

The monitoring stack provides:
- **Real-time log streaming** — aggregate logs from all API containers
- **Performance dashboards** — response time percentiles and error rates
- **Pre-configured Grafana dashboard** — with API metrics visualization
- **Zero-configuration setup** — automatic setup for drssed-api

### Quick Setup

```bash
git clone https://github.com/davidriegel/drssed-monitoring.git
cd drssed-monitoring
docker compose up -d
```

Access the monitoring dashboard at `http://localhost:3000` (default login: `admin` / `admin`).

No additional configuration required — the monitoring stack automatically discovers and monitors the API container.

For detailed setup and customization, see the [drssed-monitoring documentation](https://github.com/davidriegel/drssed-monitoring).

---

## Related

- **iOS App** → [davidriegel/drssed-ios](https://github.com/davidriegel/drssed-ios)
- **Monitoring** → [davidriegel/drssed-monitoring](https://github.com/davidriegel/drssed-monitoring)
- **Portfolio** → [davidriegel.dev](https://davidriegel.dev)

---

## About the Project

Drssed started as a personal project to solve a real problem: losing track of what clothes you own. It grew into a full-stack application with a custom backend, a relational database, image processing features and a native iOS app.

---
