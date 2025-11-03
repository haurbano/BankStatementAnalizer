# Production Deployment

This guide explains how to deploy the Statement Analyzer stack on a Linux server using Docker Compose.

## 1. Prerequisites

- Linux server with SSH access (Ubuntu 22.04+ recommended)
- `git` installed
- Docker Engine 24+ and Docker Compose plugin 2.20+
- A non-root user with `sudo` access

### Install Docker & Compose (Ubuntu example)

```bash
sudo apt-get update
sudo apt-get install -y ca-certificates curl gnupg
sudo install -m 0755 -d /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg
echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu $(. /etc/os-release && echo $VERSION_CODENAME) stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null
sudo apt-get update
sudo apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
sudo usermod -aG docker $USER
```

Log out and log back in to apply group membership.

## 2. Clone the Repository

```bash
git clone <repo-url> statement-analyzer
cd statement-analyzer
```

If you deploy from a tarball or file upload, upload the project directory to the server instead.

## 3. Environment & Configuration

- Review `docker-compose.yml` and adjust ports if needed.
- Ensure `frontend/app.js` already points to `/api` (done by default).
- Customize `backend/category_keywords.json` if required.
- Set additional environment variables (database credentials, telemetry, etc.) by editing the `environment` section in `docker-compose.yml`.

## 4. Build & Run

```bash
docker compose build
docker compose up -d
```

- The backend API listens on the internal `backend` service (port 8000 inside the network).
- The frontend is exposed on `http://<server-ip>:8080` by Nginx.

## 5. Verification

1. Check that containers are healthy:
   ```bash
   docker compose ps
   ```
2. Tail logs if you need to troubleshoot:
   ```bash
   docker compose logs -f backend
   docker compose logs -f web
   ```
3. Open `http://<server-ip>:8080` in a browser and upload a PDF.

## 6. Maintenance

- Update images after code changes:
  ```bash
  git pull
  docker compose build
  docker compose up -d
  ```
- Restart services without rebuilding:
  ```bash
  docker compose restart backend web
  ```
- Review system usage:
  ```bash
  docker system df
  ```

## 7. Backups & Persistence

The application is stateless; configuration lives in the project files. If you mount additional volumes for uploads or analytics, include them in your server backup strategy.

## 8. Security & Hardening

- Place the stack behind a reverse proxy (e.g. Traefik, Nginx, Caddy) with HTTPS in production.
- Configure a firewall to allow only required ports (e.g. 22 for SSH, 8080 for HTTP, or 80/443 if fronted by a reverse proxy).
- Keep the server OS and Docker engine up to date (`sudo apt-get upgrade` regularly).
- Enable monitoring/alerting (Prometheus, Grafana, or a managed solution) if deploying long term.

## 9. Optional Enhancements

- Use a process manager (systemd) to ensure Docker service starts on boot (`sudo systemctl enable docker`).
- Configure log rotation with Docker daemon settings (`/etc/docker/daemon.json`).
- Swap out the built-in Nginx container for your existing edge proxy if integrating into a larger platform.

## 10. Teardown

Stop the stack and remove containers:

```bash
docker compose down
```

Add `--volumes` to drop named volumes if created.

