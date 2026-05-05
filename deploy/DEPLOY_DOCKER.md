# Deploy Goals with Docker (xmeng.plus)

This stack runs **MySQL**, **Django + FastAPI** (one image, supervisord), **Nginx** (React static + reverse proxy), and **Certbot** (renewal).

**Security:** If your server password was shared in a chat or ticket, **change it in the Tencent Cloud console** and prefer **SSH keys** instead of password login.

## 1. One-time server prep (Ubuntu)

On the server (SSH as `ubuntu`), install Docker and Compose, open ports **22 / 80 / 443**, then create `/opt/goals` as below. You can copy [`deploy/setup-server.sh`](setup-server.sh) to the server and run it with `sudo`, or install Docker using [Docker’s official docs](https://docs.docker.com/engine/install/ubuntu/).

```text
/opt/goals/
  docker-compose.yml      ← from this repo: deploy/docker-compose.yml
  .env                    ← from deploy/.env.example (filled in)
  backend/                ← full **Goals** repo (Django + FastAPI)
  frontend/               ← full **Goals_Front_End** repo (React)
  nginx/
    Dockerfile
    nginx.conf            ← see SSL section below
    nginx.bootstrap.conf
    nginx.https.conf
  certbot/conf/
  certbot/www/
```

## 2. Upload code from your Mac

Replace `YOUR_SERVER_IP` with the instance public IP (or `xmeng.plus` if DNS and SSH already work).

```bash
# Backend (Goals)
rsync -avz --delete \
  --exclude '.git' --exclude '.venv' --exclude '__pycache__' --exclude '*.pyc' \
  /Users/meng/Desktop/Goals/ \
  ubuntu@YOUR_SERVER_IP:/opt/goals/backend/

# Frontend (Goals_Front_End)
rsync -avz --delete \
  --exclude 'node_modules' --exclude '.git' \
  /Users/meng/Desktop/Goals_Front_End/ \
  ubuntu@YOUR_SERVER_IP:/opt/goals/frontend/

# Deploy config
scp /Users/meng/Desktop/Goals/deploy/docker-compose.yml ubuntu@YOUR_SERVER_IP:/opt/goals/
scp /Users/meng/Desktop/Goals/deploy/.env.example ubuntu@YOUR_SERVER_IP:/opt/goals/
scp -r /Users/meng/Desktop/Goals/deploy/nginx ubuntu@YOUR_SERVER_IP:/opt/goals/
```

On the server, ensure `backend/Dockerfile` exists (it is the Dockerfile at the root of the **Goals** repo after rsync).

## 3. Environment file

On the server:

```bash
cd /opt/goals
cp .env.example .env
nano .env
```

Set at least:

- `MYSQL_ROOT_PASSWORD`
- `DB_NAME` (default `tasks`)
- `DJANGO_SECRET_KEY`
- `DJANGO_DEBUG=False`
- `DJANGO_ALLOWED_HOSTS=xmeng.plus,www.xmeng.plus,localhost,127.0.0.1`
- `CORS_EXTRA_ORIGINS=https://xmeng.plus,https://www.xmeng.plus`

`docker-compose.yml` passes `DB_HOST=db` and MySQL credentials into the backend container.

## 4. First run: HTTP-only nginx (before TLS files exist)

The default `nginx.conf` expects `/etc/letsencrypt/live/xmeng.plus/`. **If those files do not exist yet**, use the bootstrap config:

```bash
cd /opt/goals/nginx
cp nginx.bootstrap.conf nginx.conf
cd /opt/goals
sudo docker compose build --no-cache nginx
sudo docker compose up -d db
# wait for db healthy, then:
sudo docker compose up -d --build
```

Issue certificates (DNS for `xmeng.plus` / `www.xmeng.plus` must point to this server):

```bash
cd /opt/goals
sudo docker compose run --rm certbot certonly --webroot \
  -w /var/www/certbot \
  --email your@email.com --agree-tos --no-eff-email \
  -d xmeng.plus -d www.xmeng.plus
```

Switch to HTTPS config and rebuild nginx:

```bash
cd /opt/goals/nginx
cp nginx.https.conf nginx.conf
cd /opt/goals
sudo docker compose build --no-cache nginx
sudo docker compose up -d
```

## 5. Database migrations

After the backend image is up:

```bash
cd /opt/goals
sudo docker compose exec backend python manage.py migrate
sudo docker compose exec backend python manage.py collectstatic --noinput
```

(If you restore from SQL, do that before or after migrate per your backup docs.)

## 6. Frontend API URL

Production builds use **same-origin** API calls: `API_BASE_URL` is empty when `VITE_API_BASE_URL` is not set, so `/api/...` goes through Nginx to FastAPI.

Optional explicit build arg:

```dockerfile
# In nginx/Dockerfile build, or pass:
# docker compose build --build-arg VITE_API_BASE_URL=https://xmeng.plus nginx
```

Usually **not required**.

## 7. Deploy updates (after initial setup)

From your Mac:

```bash
rsync ... Goals/       → /opt/goals/backend/
rsync ... Goals_Front_End/ → /opt/goals/frontend/
```

On the server:

```bash
cd /opt/goals
sudo docker compose build --no-cache backend nginx
sudo docker compose up -d
```

## Troubleshooting

- **`nginx` exits / SSL error:** Use `nginx.bootstrap.conf` until Certbot has created `live/xmeng.plus`.
- **CORS:** add your site to `CORS_EXTRA_ORIGINS` in `.env` and rebuild **backend** (FastAPI reads env at start).
- **Media/static:** Served via Nginx volumes `media_data` / `static_data`; do not delete those volumes unless you intend to reset files.
