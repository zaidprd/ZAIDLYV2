#!/bin/bash
# Deploy SEO.Zaidly ke VPS Ubuntu
# Jalankan sebagai root atau user dengan sudo

set -e

APP_DIR=/var/www/seozaidly
REPO_URL=https://github.com/yourusername/seozaidly.git

echo "=== Deploy SEO.Zaidly ==="

# 1. Install system dependencies
apt-get update -q
apt-get install -y python3.11 python3.11-venv python3-pip postgresql nginx

# 2. Setup PostgreSQL
echo "Setup PostgreSQL..."
sudo -u postgres psql -c "CREATE DATABASE seozaidly;" 2>/dev/null || true
sudo -u postgres psql -c "CREATE USER seozaidly WITH PASSWORD '${DB_PASSWORD}';" 2>/dev/null || true
sudo -u postgres psql -c "GRANT ALL PRIVILEGES ON DATABASE seozaidly TO seozaidly;" 2>/dev/null || true

# 3. Clone / pull repo
if [ -d "$APP_DIR" ]; then
    cd $APP_DIR && git pull
else
    git clone $REPO_URL $APP_DIR
    cd $APP_DIR
fi

# 4. Python virtualenv
python3.11 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# 5. Run migrations & collect static
python manage.py migrate --noinput
python manage.py collectstatic --noinput

# 6. Directories
mkdir -p /run/seozaidly /var/log/seozaidly
chown www-data:www-data /run/seozaidly /var/log/seozaidly

# 7. Systemd services
cp deploy/seozaidly-web.service /etc/systemd/system/
cp deploy/seozaidly-hermes.service /etc/systemd/system/
systemctl daemon-reload
systemctl enable seozaidly-web seozaidly-hermes
systemctl restart seozaidly-web seozaidly-hermes

# 8. Nginx
cp deploy/nginx.conf /etc/nginx/sites-available/seozaidly
ln -sf /etc/nginx/sites-available/seozaidly /etc/nginx/sites-enabled/seozaidly
nginx -t && systemctl reload nginx

echo "=== Deploy selesai ==="
echo "Cek status: systemctl status seozaidly-web seozaidly-hermes"
