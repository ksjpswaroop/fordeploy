#!/bin/bash

# =============================================================================
# DIGITALOCEAN DROPLET SETUP SCRIPT
# =============================================================================
# This script sets up a fresh DigitalOcean droplet for the AI Recruitment Platform
# Run this script on your droplet after initial creation
# Usage: curl -sSL https://raw.githubusercontent.com/yourusername/yourrepo/main/scripts/setup-server.sh | bash

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Configuration
APP_DIR="/opt/ai-recruitment-platform"
APP_USER="appuser"

# Update system
update_system() {
    log_info "Updating system packages..."
    apt-get update
    apt-get upgrade -y
    log_success "System updated successfully."
}

# Install Docker
install_docker() {
    log_info "Installing Docker..."
    
    # Remove old versions
    apt-get remove -y docker docker-engine docker.io containerd runc || true
    
    # Install dependencies
    apt-get install -y \
        ca-certificates \
        curl \
        gnupg \
        lsb-release
    
    # Add Docker's official GPG key
    mkdir -p /etc/apt/keyrings
    curl -fsSL https://download.docker.com/linux/ubuntu/gpg | gpg --dearmor -o /etc/apt/keyrings/docker.gpg
    
    # Set up repository
    echo \
        "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu \
        $(lsb_release -cs) stable" | tee /etc/apt/sources.list.d/docker.list > /dev/null
    
    # Install Docker Engine
    apt-get update
    apt-get install -y docker-ce docker-ce-cli containerd.io docker-compose-plugin
    
    # Start and enable Docker
    systemctl start docker
    systemctl enable docker
    
    log_success "Docker installed successfully."
}

# Install Docker Compose
install_docker_compose() {
    log_info "Installing Docker Compose..."
    
    # Install Docker Compose v2 (if not already installed with Docker)
    if ! command -v docker-compose &> /dev/null; then
        curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
        chmod +x /usr/local/bin/docker-compose
    fi
    
    log_success "Docker Compose installed successfully."
}

# Install DigitalOcean CLI
install_doctl() {
    log_info "Installing DigitalOcean CLI (doctl)..."
    
    cd /tmp
    wget https://github.com/digitalocean/doctl/releases/latest/download/doctl-1.94.0-linux-amd64.tar.gz
    tar xf doctl-1.94.0-linux-amd64.tar.gz
    mv doctl /usr/local/bin
    
    log_success "doctl installed successfully."
}

# Install additional tools
install_tools() {
    log_info "Installing additional tools..."
    
    apt-get install -y \
        git \
        curl \
        wget \
        unzip \
        htop \
        nginx \
        certbot \
        python3-certbot-nginx \
        ufw \
        fail2ban \
        logrotate
    
    log_success "Additional tools installed successfully."
}

# Configure firewall
configure_firewall() {
    log_info "Configuring firewall..."
    
    # Reset UFW to defaults
    ufw --force reset
    
    # Set default policies
    ufw default deny incoming
    ufw default allow outgoing
    
    # Allow SSH (adjust port if you changed it)
    ufw allow 22/tcp
    
    # Allow HTTP and HTTPS
    ufw allow 80/tcp
    ufw allow 443/tcp
    
    # Allow application ports (only if needed for direct access)
    # ufw allow 3000/tcp  # Frontend (usually behind nginx)
    # ufw allow 8080/tcp  # Backend API (usually behind nginx)
    
    # Enable firewall
    ufw --force enable
    
    log_success "Firewall configured successfully."
}

# Configure fail2ban
configure_fail2ban() {
    log_info "Configuring fail2ban..."
    
    cat > /etc/fail2ban/jail.local << EOF
[DEFAULT]
bantime = 3600
findtime = 600
maxretry = 3

[sshd]
enabled = true
port = ssh
filter = sshd
logpath = /var/log/auth.log
maxretry = 3

[nginx-http-auth]
enabled = true
filter = nginx-http-auth
port = http,https
logpath = /var/log/nginx/error.log

[nginx-limit-req]
enabled = true
filter = nginx-limit-req
port = http,https
logpath = /var/log/nginx/error.log
maxretry = 10
EOF
    
    systemctl restart fail2ban
    systemctl enable fail2ban
    
    log_success "fail2ban configured successfully."
}

# Create application user
create_app_user() {
    log_info "Creating application user..."
    
    if ! id "$APP_USER" &>/dev/null; then
        useradd -m -s /bin/bash "$APP_USER"
        usermod -aG docker "$APP_USER"
        log_success "User $APP_USER created successfully."
    else
        log_warning "User $APP_USER already exists."
    fi
}

# Setup application directory
setup_app_directory() {
    log_info "Setting up application directory..."
    
    mkdir -p "$APP_DIR"
    chown -R "$APP_USER:$APP_USER" "$APP_DIR"
    
    # Create necessary subdirectories
    mkdir -p "$APP_DIR"/{uploads,generated_docs,logs,backups,nginx,ssl}
    chown -R "$APP_USER:$APP_USER" "$APP_DIR"
    
    log_success "Application directory setup completed."
}

# Configure log rotation
configure_logrotate() {
    log_info "Configuring log rotation..."
    
    cat > /etc/logrotate.d/ai-recruitment << EOF
$APP_DIR/logs/*.log {
    daily
    missingok
    rotate 30
    compress
    delaycompress
    notifempty
    create 644 $APP_USER $APP_USER
    postrotate
        docker-compose -f $APP_DIR/docker-compose.prod.yml restart api web || true
    endscript
}
EOF
    
    log_success "Log rotation configured successfully."
}

# Setup SSL with Let's Encrypt (placeholder)
setup_ssl_placeholder() {
    log_info "Setting up SSL certificate placeholder..."
    
    cat > "$APP_DIR/setup-ssl.sh" << 'EOF'
#!/bin/bash
# SSL Setup Script
# Run this after your domain is pointing to this server

DOMAIN="yourdomain.com"
EMAIL="your-email@domain.com"

# Stop nginx if running
systemctl stop nginx

# Get certificate
certbot certonly --standalone -d $DOMAIN -d www.$DOMAIN --email $EMAIL --agree-tos --non-interactive

# Configure nginx for SSL
# Update your nginx configuration to use the certificates
# Certificates will be in: /etc/letsencrypt/live/$DOMAIN/

# Restart nginx
systemctl start nginx

# Setup auto-renewal
echo "0 12 * * * /usr/bin/certbot renew --quiet" | crontab -
EOF
    
    chmod +x "$APP_DIR/setup-ssl.sh"
    chown "$APP_USER:$APP_USER" "$APP_DIR/setup-ssl.sh"
    
    log_success "SSL setup script created at $APP_DIR/setup-ssl.sh"
}

# Configure system limits
configure_system_limits() {
    log_info "Configuring system limits..."
    
    cat >> /etc/security/limits.conf << EOF
# AI Recruitment Platform limits
$APP_USER soft nofile 65536
$APP_USER hard nofile 65536
$APP_USER soft nproc 4096
$APP_USER hard nproc 4096
EOF
    
    # Configure systemd limits
    mkdir -p /etc/systemd/system.conf.d
    cat > /etc/systemd/system.conf.d/limits.conf << EOF
[Manager]
DefaultLimitNOFILE=65536
DefaultLimitNPROC=4096
EOF
    
    log_success "System limits configured successfully."
}

# Setup monitoring (basic)
setup_monitoring() {
    log_info "Setting up basic monitoring..."
    
    # Create monitoring script
    cat > "$APP_DIR/monitor.sh" << 'EOF'
#!/bin/bash
# Basic monitoring script

LOG_FILE="/var/log/ai-recruitment-monitor.log"

check_services() {
    echo "$(date): Checking services..." >> $LOG_FILE
    
    # Check Docker containers
    if ! docker-compose -f /opt/ai-recruitment-platform/docker-compose.prod.yml ps | grep -q "Up"; then
        echo "$(date): WARNING - Some containers are not running" >> $LOG_FILE
        # Add notification logic here (email, Slack, etc.)
    fi
    
    # Check disk space
    DISK_USAGE=$(df / | awk 'NR==2 {print $5}' | sed 's/%//')
    if [ $DISK_USAGE -gt 80 ]; then
        echo "$(date): WARNING - Disk usage is ${DISK_USAGE}%" >> $LOG_FILE
    fi
    
    # Check memory usage
    MEM_USAGE=$(free | awk 'NR==2{printf "%.0f", $3*100/$2}')
    if [ $MEM_USAGE -gt 90 ]; then
        echo "$(date): WARNING - Memory usage is ${MEM_USAGE}%" >> $LOG_FILE
    fi
}

check_services
EOF
    
    chmod +x "$APP_DIR/monitor.sh"
    chown "$APP_USER:$APP_USER" "$APP_DIR/monitor.sh"
    
    # Add to crontab
    echo "*/5 * * * * $APP_DIR/monitor.sh" | crontab -u "$APP_USER" -
    
    log_success "Basic monitoring setup completed."
}

# Main setup function
main() {
    log_info "Starting DigitalOcean droplet setup for AI Recruitment Platform..."
    
    # Check if running as root
    if [ "$EUID" -ne 0 ]; then
        log_error "Please run this script as root (use sudo)"
        exit 1
    fi
    
    update_system
    install_docker
    install_docker_compose
    install_doctl
    install_tools
    configure_firewall
    configure_fail2ban
    create_app_user
    setup_app_directory
    configure_logrotate
    setup_ssl_placeholder
    configure_system_limits
    setup_monitoring
    
    log_success "Server setup completed successfully!"
    
    echo ""
    echo "=========================="
    echo "SETUP COMPLETE"
    echo "=========================="
    echo "Next steps:"
    echo "1. Clone your repository to $APP_DIR"
    echo "2. Copy .env.production to .env and configure your settings"
    echo "3. Run the deployment script: $APP_DIR/scripts/deploy.sh"
    echo "4. Configure SSL: $APP_DIR/setup-ssl.sh (after domain setup)"
    echo ""
    echo "Important files:"
    echo "- Application directory: $APP_DIR"
    echo "- SSL setup script: $APP_DIR/setup-ssl.sh"
    echo "- Monitoring script: $APP_DIR/monitor.sh"
    echo ""
    echo "Security notes:"
    echo "- Firewall is enabled (ports 22, 80, 443)"
    echo "- fail2ban is configured"
    echo "- Consider changing SSH port and disabling password auth"
    echo "=========================="
}

# Run main function
main "$@"