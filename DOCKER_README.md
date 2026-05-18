# Docker Setup Guide

This guide explains how to containerize and run the Streamlit data processing application using Docker.

## Prerequisites

- **Docker** (version 20.10+): [Install Docker](https://docs.docker.com/get-docker/)
- **Docker Compose** (version 2.0+): Usually included with Docker Desktop
- **Supabase credentials**: You'll need your Supabase project URL and API key

## Quick Start (Recommended)

### 1. Set up environment variables

Copy the example environment file and fill in your Supabase credentials:

```bash
cp .env.example .env
```

Edit `.env` and add your Supabase credentials:
```
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_KEY=your-supabase-api-key
```

### 2. Build and run with Docker Compose

```bash
docker-compose up
```

The app will be available at **http://localhost:8501**

To run in the background:
```bash
docker-compose up -d
```

To stop:
```bash
docker-compose down
```

To view logs:
```bash
docker-compose logs -f streamlit
```

---

## Manual Docker Commands (Alternative)

If you prefer to use Docker directly without Compose:

### 1. Build the image

```bash
docker build -t streamlit-app .
```

### 2. Create .env file

```bash
cp .env.example .env
# Edit .env with your Supabase credentials
```

### 3. Run the container

```bash
docker run -p 8501:8501 --env-file .env streamlit-app
```

Or with volume mount for hot-reload during development:

```bash
docker run -p 8501:8501 --env-file .env -v "$(pwd):/service" streamlit-app
```

---

## Features

✅ **Hot Reload**: Code changes automatically reload the app (with volume mount)  
✅ **Environment Variables**: All Supabase credentials loaded from `.env`  
✅ **Health Check**: Container has built-in health monitoring  
✅ **Lightweight**: Uses Python 3.10 slim image (~180MB)  
✅ **Development Ready**: Easily switch to production configs

---

## Troubleshooting

### Port already in use (8501)

If port 8501 is already in use, map to a different port:

```bash
docker run -p 8000:8501 --env-file .env streamlit-app
```

Then access the app at **http://localhost:8000**

### App crashes on startup

Check the logs:

```bash
docker-compose logs streamlit
```

Common issues:
- **Missing `.env` file**: Copy `.env.example` to `.env` and add credentials
- **Invalid Supabase credentials**: Verify `SUPABASE_URL` and `SUPABASE_KEY` are correct
- **Network issues**: Ensure you have internet access to reach Supabase

### App seems slow or unresponsive

Check container resource usage:

```bash
docker stats streamlit-app
```

If memory/CPU is maxed out, increase Docker resources in Docker Desktop settings.

### Build fails with "No module named X"

Rebuild without cache:

```bash
docker-compose build --no-cache
docker-compose up
```

---

## Docker Image Details

- **Base Image**: `python:3.10-slim` (~180 MB)
- **Python Version**: 3.10 (production-standard)
- **Dependencies**: Streamlit, Supabase, pandas, numpy, python-dotenv
- **Port**: 8501 (Streamlit default)
- **Health Check**: Enabled with 30s interval

---

## Volume Mounts (Development)

The docker-compose.yml includes a volume mount for development:

```yaml
volumes:
  - .:/service  # Mount current directory for hot-reload
```

This allows you to:
- Edit code in your IDE
- See changes instantly in the running app
- Debug locally without rebuilding

To disable hot-reload for production, remove the volume mount.

---

## Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `SUPABASE_URL` | ✅ Yes | Your Supabase project URL |
| `SUPABASE_KEY` | ✅ Yes | Your Supabase API key (anon/public) |
| `PORT` | ❌ No | Port to run Streamlit on (default: 8501) |
| `ENVIRONMENT` | ❌ No | deployment environment (development/staging/production) |

---

## Next Steps

### For Local Development
- Add the volume mount for code hot-reload
- Use `docker-compose up` for easy start/stop
- Check logs with `docker-compose logs -f`

### For Production Deployment
- Use a production registry (DockerHub, Azure ACR, etc.)
- Tag image: `docker build -t myregistry/streamlit-app:v1.0 .`
- Push to registry: `docker push myregistry/streamlit-app:v1.0`
- Deploy with Kubernetes, Docker Swarm, or cloud container services
- Remove volume mounts and set environment to `production`

### Further Optimizations
- **Multi-stage build**: Reduce image size for production
- **CI/CD integration**: Automate builds and tests
- **Container orchestration**: Deploy with Docker Swarm or Kubernetes
- **Monitoring**: Add Prometheus/Grafana for metrics

---

## Questions or Issues?

Refer to the main [README.md](README.md) for app-specific documentation, or consult the [Streamlit documentation](https://docs.streamlit.io/).
