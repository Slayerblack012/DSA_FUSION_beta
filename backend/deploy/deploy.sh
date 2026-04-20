#!/bin/bash
# ===========================================
# DSA AutoGrader - Production Deployment Script
# ===========================================
# Deploy to Linux server without Docker
# ===========================================

set -e

# Configuration
APP_NAME="dsa-autograder"
APP_USER="dsa"
APP_DIR="/opt/dsa-autograder"
PYTHON_VENV="${APP_DIR}/venv"
SYSTEMD_SERVICE="/etc/systemd/system/${APP_NAME}.service"
LOG_DIR="/var/log/${APP_NAME}"
DATA_DIR="/var/lib/${APP_NAME}"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

echo_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

echo_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if running as root
if [ "$EUID" -ne 0 ]; then
    echo_error "Please run as root (sudo ./deploy.sh)"
    exit 1
fi

# ===========================================
# 1. Install System Dependencies
# ===========================================
echo_info "Installing system dependencies..."

apt update
apt install -y \
    python3.11 \
    python3.11-venv \
    python3-pip \
    redis-server \
    nginx \
    supervisor \
    git \
    curl \
    wget \
    build-essential \
    unrar

# ===========================================
# 2. Create Application User
# ===========================================
echo_info "Creating application user..."

if ! id -u ${APP_USER} > /dev/null 2>&1; then
    useradd --system --no-create-home --shell /bin/false ${APP_USER}
    echo_info "User ${APP_USER} created"
else
    echo_warn "User ${APP_USER} already exists"
fi

# ===========================================
# 3. Create Directories
# ===========================================
echo_info "Creating directories..."

mkdir -p ${APP_DIR}
mkdir -p ${LOG_DIR}
mkdir -p ${DATA_DIR}

chown -R ${APP_USER}:${APP_USER} ${APP_DIR}
chown -R ${APP_USER}:${APP_USER} ${LOG_DIR}
chown -R ${APP_USER}:${APP_USER} ${DATA_DIR}

# ===========================================
# 4. Setup Redis
# ===========================================
echo_info "Setting up Redis..."

systemctl enable redis-server
systemctl start redis-server

# Test Redis
if redis-cli ping > /dev/null 2>&1; then
    echo_info "Redis is running"
else
    echo_error "Redis failed to start"
    exit 1
fi

# ===========================================
# 5. Deploy Application
# ===========================================
echo_info "Deploying application..."

# Copy application files
cp -r . ${APP_DIR}/

cd ${APP_DIR}

# Create virtual environment
if [ ! -d "${PYTHON_VENV}" ]; then
    python3.11 -m venv ${PYTHON_VENV}
    echo_info "Virtual environment created"
fi

# Activate virtual environment
source ${PYTHON_VENV}/bin/activate

# Upgrade pip
pip install --upgrade pip

# Install dependencies
pip install -r requirements.txt
pip install gunicorn

# Create .env file if not exists
if [ ! -f "${APP_DIR}/.env" ]; then
    echo_warn ".env file not found. Please create it manually."
    echo_warn "Copy .env.example to .env and fill in your credentials"
fi

# ===========================================
# 6. Create Systemd Service
# ===========================================
echo_info "Creating systemd service..."

cat > ${SYSTEMD_SERVICE} << EOF
[Unit]
Description=DSA AutoGrader Service
After=network.target redis-server.service

[Service]
Type=notify
User=${APP_USER}
Group=${APP_USER}
WorkingDirectory=${APP_DIR}
Environment="PATH=${PYTHON_VENV}/bin"
ExecStart=${PYTHON_VENV}/bin/gunicorn app.main:app \\
    --workers 4 \\
    --worker-class uvicorn.workers.UvicornWorker \\
    --bind 0.0.0.0:8000 \\
    --timeout 120 \\
    --access-logfile ${LOG_DIR}/access.log \\
    --error-logfile ${LOG_DIR}/error.log \\
    --capture-output \\
    --enable-stdio-inheritance
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal
SyslogIdentifier=${APP_NAME}

# Security hardening
NoNewPrivileges=true
PrivateTmp=true

[Install]
WantedBy=multi-user.target
EOF

# Reload systemd
systemctl daemon-reload
systemctl enable ${APP_NAME}

# ===========================================
# 7. Configure Nginx (Reverse Proxy)
# ===========================================
echo_info "Configuring Nginx..."

cat > /etc/nginx/sites-available/${APP_NAME} << EOF
server {
    listen 80;
    server_name _;
    
    # Logging
    access_log ${LOG_DIR}/nginx_access.log;
    error_log ${LOG_DIR}/nginx_error.log;
    
    # Client upload size limit
    client_max_body_size 20M;
    
    # Proxy settings
    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade \$http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
        proxy_cache_bypass \$http_upgrade;
        proxy_read_timeout 120s;
        proxy_connect_timeout 60s;
    }
    
    # Health check endpoint
    location /health {
        proxy_pass http://127.0.0.1:8000/health;
    }
    
    # Metrics endpoint (restrict to internal)
    location /metrics {
        allow 127.0.0.1;
        deny all;
        proxy_pass http://127.0.0.1:8000/metrics;
    }
}
EOF

# Enable Nginx site
ln -sf /etc/nginx/sites-available/${APP_NAME} /etc/nginx/sites-enabled/
nginx -t
systemctl restart nginx

# ===========================================
# 8. Setup Firewall (UFW)
# ===========================================
echo_info "Configuring firewall..."

ufw allow 'Nginx Full'
ufw allow 'SSH'
ufw --force enable

# ===========================================
# 9. Start Application
# ===========================================
echo_info "Starting application..."

systemctl start ${APP_NAME}

# Wait for service to start
sleep 5

# Check status
if systemctl is-active --quiet ${APP_NAME}; then
    echo_info "Application started successfully!"
else
    echo_error "Application failed to start"
    systemctl status ${APP_NAME}
    exit 1
fi

# ===========================================
# 10. Verify Deployment
# ===========================================
echo_info "Verifying deployment..."

# Health check
if curl -f http://localhost/health > /dev/null 2>&1; then
    echo_info "Health check passed"
else
    echo_warn "Health check failed - application may still be starting"
fi

# ===========================================
# Summary
# ===========================================
echo ""
echo "============================================"
echo_info "DEPLOYMENT COMPLETED!"
echo "============================================"
echo ""
echo "Application URLs:"
echo "  - Web UI: http://$(hostname -I | awk '{print $1}')"
echo "  - API Docs: http://$(hostname -I | awk '{print $1}')/docs"
echo "  - Health: http://$(hostname -I | awk '{print $1}')/health"
echo ""
echo "Logs:"
echo "  - Application: ${LOG_DIR}/"
echo "  - Systemd: journalctl -u ${APP_NAME}"
echo ""
echo "Commands:"
echo "  - Status: systemctl status ${APP_NAME}"
echo "  - Restart: systemctl restart ${APP_NAME}"
echo "  - Logs: journalctl -u ${APP_NAME} -f"
echo ""
echo "============================================"
