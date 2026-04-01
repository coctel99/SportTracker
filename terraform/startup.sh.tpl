#!/bin/bash
set -euo pipefail
exec > /var/log/startup-script.log 2>&1

# Docker
curl -fsSL https://get.docker.com | sh
usermod -aG docker ${ssh_user}

# nginx
apt-get install -y nginx

# GitHub Actions deploy key (for CD: GitHub Actions → VM)
mkdir -p /home/${ssh_user}/.ssh
echo '${deploy_public_key}' >> /home/${ssh_user}/.ssh/authorized_keys
chmod 700 /home/${ssh_user}/.ssh
chmod 600 /home/${ssh_user}/.ssh/authorized_keys
chown -R ${ssh_user}:${ssh_user} /home/${ssh_user}/.ssh

# Clone repo (public repo — HTTPS, no credentials needed)
sudo -u ${ssh_user} git clone ${github_repo} ${app_dir}

# Write .env
cat > ${app_dir}/.env <<ENVFILE
SPORT_TRACKER_SECRET_KEY=${secret_key}
SPORT_TRACKER_DEBUG=false
SPORT_TRACKER_DATABASE=/app/instance/sport_tracker.sqlite
SPORT_TRACKER_HTTPS=false
ENVFILE
chown ${ssh_user}:${ssh_user} ${app_dir}/.env

# nginx config
cat > /etc/nginx/sites-available/sport-tracker <<NGINXCONF
server {
    listen 80 default_server;
    server_name _;
    location / {
        proxy_pass         http://127.0.0.1:8000;
        proxy_set_header   Host              \$host;
        proxy_set_header   X-Real-IP         \$remote_addr;
        proxy_set_header   X-Forwarded-For   \$proxy_add_x_forwarded_for;
        proxy_set_header   X-Forwarded-Proto \$scheme;
    }
}
NGINXCONF

rm -f /etc/nginx/sites-enabled/default
ln -s /etc/nginx/sites-available/sport-tracker /etc/nginx/sites-enabled/
nginx -t && systemctl restart nginx

# Start app
cd ${app_dir}
sudo -u ${ssh_user} docker compose up -d --build
