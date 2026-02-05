#!/bin/bash
# ==========================================
# LabOS Deployment Script
# ==========================================

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# VM Configuration
VM_NAME="stella-vm"
VM_ZONE="us-central1-a"

# Get VM IP from gcloud
get_vm_ip() {
    gcloud compute instances describe $VM_NAME --zone=$VM_ZONE --format='get(networkInterfaces[0].accessConfigs[0].natIP)' 2>/dev/null
}

# Usage
usage() {
    echo "Usage: $0 [dev|prod|stop|logs|status|ssh|deploy|ip]"
    echo ""
    echo "Local Commands:"
    echo "  dev     - Start development environment (local)"
    echo "  prod    - Start production environment (local with VM_IP)"
    echo "  stop    - Stop all containers"
    echo "  logs    - Show container logs"
    echo "  status  - Show container status"
    echo ""
    echo "VM Commands:"
    echo "  ip      - Get VM external IP"
    echo "  ssh     - SSH into VM"
    echo "  deploy  - Deploy to VM (copy files + start)"
    exit 1
}

# Load .env if exists
if [ -f ".env" ]; then
    export $(grep -v '^#' .env | xargs)
fi

# Auto-detect VM_IP if not set
if [ -z "$VM_IP" ]; then
    VM_IP=$(get_vm_ip 2>/dev/null || echo "")
fi

case "$1" in
    dev)
        echo -e "${GREEN}Starting LabOS in development mode...${NC}"
        docker-compose -f docker-compose.yml -f docker-compose.dev.yml up --build
        ;;
    prod)
        if [ -z "$VM_IP" ]; then
            echo -e "${RED}Error: Cannot get VM_IP. Check gcloud auth.${NC}"
            exit 1
        fi
        echo -e "${GREEN}Starting LabOS in production mode...${NC}"
        echo -e "VM_IP: ${VM_IP}"
        export VM_IP
        docker-compose -f docker-compose.yml -f docker-compose.prod.yml up -d --build
        echo -e "${GREEN}Done! Access at http://${VM_IP}:3000${NC}"
        ;;
    stop)
        echo -e "${YELLOW}Stopping LabOS...${NC}"
        docker-compose -f docker-compose.yml -f docker-compose.dev.yml down 2>/dev/null || true
        docker-compose -f docker-compose.yml -f docker-compose.prod.yml down 2>/dev/null || true
        echo -e "${GREEN}Stopped.${NC}"
        ;;
    logs)
        docker-compose logs -f
        ;;
    status)
        docker-compose ps
        ;;
    ip)
        if [ -z "$VM_IP" ]; then
            echo -e "${RED}Cannot get VM IP${NC}"
            exit 1
        fi
        echo -e "${GREEN}VM External IP: ${VM_IP}${NC}"
        ;;
    ssh)
        echo -e "${GREEN}Connecting to ${VM_NAME}...${NC}"
        gcloud compute ssh $VM_NAME --zone=$VM_ZONE
        ;;
    deploy)
        if [ -z "$VM_IP" ]; then
            echo -e "${RED}Error: Cannot get VM_IP${NC}"
            exit 1
        fi
        echo -e "${GREEN}Deploying to ${VM_NAME} (${VM_IP})...${NC}"

        # Create deployment directory on VM
        gcloud compute ssh $VM_NAME --zone=$VM_ZONE --command="mkdir -p ~/labos"

        # Copy files to VM (excluding .git, node_modules, etc.)
        gcloud compute scp --zone=$VM_ZONE --recurse \
            docker-compose.yml \
            docker-compose.prod.yml \
            backend \
            frontend \
            $VM_NAME:~/labos/

        # Start containers on VM
        gcloud compute ssh $VM_NAME --zone=$VM_ZONE --command="
            cd ~/labos
            export VM_IP=${VM_IP}
            docker-compose -f docker-compose.yml -f docker-compose.prod.yml up -d --build
        "

        echo -e "${GREEN}Deployed! Access at http://${VM_IP}:3000${NC}"
        ;;
    *)
        usage
        ;;
esac
