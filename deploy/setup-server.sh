#!/bin/bash
set -e

echo "========================================="
echo "  Goals App — Server Setup Script"
echo "========================================="

# 1. Update system
echo "[1/6] Updating system packages..."
apt-get update && apt-get upgrade -y

# 2. Install Docker
echo "[2/6] Installing Docker..."
if ! command -v docker &> /dev/null; then
    curl -fsSL https://get.docker.com | sh
    systemctl enable docker
    systemctl start docker
    echo "Docker installed successfully."
else
    echo "Docker already installed."
fi

# 3. Install Docker Compose plugin
echo "[3/6] Checking Docker Compose..."
if ! docker compose version &> /dev/null; then
    apt-get install -y docker-compose-plugin
fi
docker compose version

# 4. Create project directory
echo "[4/6] Setting up project directory..."
mkdir -p /opt/goals/{backend,frontend,nginx,certbot/conf,certbot/www,backups}

echo "[5/6] Project structure:"
echo "  /opt/goals/"
echo "  ├── docker-compose.yml"
echo "  ├── .env"
echo "  ├── backend/          ← upload Goals code here"
echo "  ├── frontend/         ← upload Goals_Front_End code here"
echo "  ├── nginx/"
echo "  │   ├── Dockerfile"
echo "  │   └── nginx.conf"
echo "  ├── certbot/"
echo "  └── backups/"

# 5. Set up firewall
echo "[6/6] Configuring firewall..."
if command -v ufw &> /dev/null; then
    ufw allow 22/tcp
    ufw allow 80/tcp
    ufw allow 443/tcp
    ufw --force enable
    echo "Firewall configured (22, 80, 443 open)."
fi

echo ""
echo "========================================="
echo "  Server setup complete!"
echo "========================================="
echo ""
echo "Next steps:"
echo "  1. Upload backend code to /opt/goals/backend/"
echo "  2. Upload frontend code to /opt/goals/frontend/"
echo "  3. Copy deploy files:"
echo "     - docker-compose.yml → /opt/goals/"
echo "     - nginx/ → /opt/goals/nginx/"
echo "     - .env → /opt/goals/.env (fill in real values)"
echo "  4. Import database backup:"
echo "     docker compose up -d db"
echo "     docker compose exec -T db mysql -uroot -p\$MYSQL_ROOT_PASSWORD tasks < backups/goals_backup.sql"
echo "  5. Run migrations:"
echo "     docker compose run --rm backend python manage.py migrate"
echo "  6. Start all services:"
echo "     cd /opt/goals && docker compose up -d --build"
echo "  7. Get SSL certificate:"
echo "     docker compose run --rm certbot certonly --webroot -w /var/www/certbot -d xmeng.plus -d www.xmeng.plus"
echo ""
