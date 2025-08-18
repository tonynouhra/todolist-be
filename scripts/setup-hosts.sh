#!/bin/bash

# Script to add custom domain entries to /etc/hosts for local development

echo "Setting up local domain mapping for TodoList API..."

# Check if running with sudo
if [ "$EUID" -ne 0 ]; then
    echo "This script needs to modify /etc/hosts and requires sudo privileges."
    echo "Please run: sudo ./scripts/setup-hosts.sh"
    exit 1
fi

# Backup original hosts file
cp /etc/hosts /etc/hosts.backup.$(date +%Y%m%d_%H%M%S)

# Domain entries to add
DOMAINS=(
    "127.0.0.1 api.todolist.local"
    "127.0.0.1 todolist-api.local"
    "127.0.0.1 todolist.local"
)

echo "Adding domain entries to /etc/hosts..."

# Add entries if they don't exist
for domain in "${DOMAINS[@]}"; do
    if ! grep -q "$domain" /etc/hosts; then
        echo "$domain" >> /etc/hosts
        echo "Added: $domain"
    else
        echo "Already exists: $domain"
    fi
done

echo ""
echo "✅ Domain setup complete!"
echo ""
echo "You can now access the API using:"
echo "  - http://api.todolist.local"
echo "  - http://todolist-api.local"
echo ""
echo "API Documentation:"
echo "  - http://api.todolist.local/docs"
echo "  - http://todolist-api.local/docs"
echo ""
echo "To remove these entries later, restore from backup:"
echo "  sudo cp /etc/hosts.backup.* /etc/hosts"