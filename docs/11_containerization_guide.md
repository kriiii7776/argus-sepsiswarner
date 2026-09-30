# SepsisGuard AI Containerization Guide

This document outlines the containerization strategy for the SepsisGuard AI prototype. The entire stack is orchestrated using Docker Compose, ensuring a reproducible, isolated, and easy-to-start local development and testing environment.

## 1. Architecture Overview

The system is containerized into five core services:
1.  **frontend**: React frontend served via an Nginx reverse proxy.
2.  **backend**: FastAPI backend application.
3.  **inference**: Dedicated FastAPI ML inference microservice.
4.  **db**: PostgreSQL database for persistent storage (users, audit logs, predictions).
5.  **redis**: Redis for caching and potential asynchronous task queues (e.g., Celery).

## 2. Installation & Prerequisites

To run this prototype locally, you must have the following installed on your host machine:
*   [Docker](https://docs.docker.com/get-docker/)
*   [Docker Compose](https://docs.docker.com/compose/install/) (v2+ recommended)
*   Git

## 3. Configuration

Before starting the stack, you must configure the environment variables:

1.  Copy the example environment file:
    ```bash
    cp .env.example .env
    ```
2.  Open the `.env` file and modify the values if necessary (e.g., change the default database passwords for enhanced security).

The `docker-compose.yml` file automatically maps these variables into the relevant containers.

## 4. Startup

To build and start the entire SepsisGuard AI prototype, run the following command from the root directory of the project:

```bash
docker-compose up -d --build
```

**What happens during startup?**
1.  Docker builds the images for the `frontend`, `backend`, and `inference` services based on their respective Dockerfiles.
2.  The `db` (PostgreSQL) and `redis` containers are pulled from Docker Hub and started first.
3.  **Health Checks & Dependencies**: The `backend` container waits until the `db`, `redis`, and `inference` containers are fully healthy before starting its API server.
4.  Persistent storage volumes (`postgres_data`) are mounted to ensure database state survives container restarts.

**Accessing the Services:**
*   **Frontend UI**: `http://localhost:80`
*   **Backend API Docs (Swagger)**: `http://localhost:8000/docs`
*   **Inference API Docs**: `http://localhost:8001/docs`

## 5. Shutdown

To stop the containers while preserving your database data:
```bash
docker-compose down
```

To stop the containers and completely wipe all persistent volumes (including the database):
```bash
docker-compose down -v
```

## 6. Troubleshooting

*   **Containers failing to start due to dependencies**: Check the status of the health checks. Run `docker ps` to see which container is unhealthy.
*   **View Logs**: To inspect the logs of a specific service (e.g., the backend), use:
    ```bash
    docker-compose logs -f backend
    ```
*   **Database connection errors in Backend**: Ensure the credentials in `.env` match what was used when the PostgreSQL volume was first initialized. If you changed passwords after the first run, you may need to clear the volume (`docker-compose down -v`) and restart.
*   **Missing requirements**: If a Python dependency is missing, add it to the `requirements.txt` in the respective directory (`src/backend` or `src/inference`) and rebuild the stack using `docker-compose up -d --build`.
