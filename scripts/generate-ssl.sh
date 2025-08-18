#!/bin/bash

# Script to generate self-signed SSL certificates for local development

echo "Generating self-signed SSL certificates for local development..."

# Create SSL directory if it doesn't exist
mkdir -p nginx/ssl

# Generate private key
openssl genrsa -out nginx/ssl/todolist.key 2048

# Generate certificate signing request
openssl req -new -key nginx/ssl/todolist.key -out nginx/ssl/todolist.csr -subj "/C=US/ST=CA/L=San Francisco/O=TodoList/CN=api.todolist.local/emailAddress=admin@todolist.local"

# Generate self-signed certificate
openssl x509 -req -days 365 -in nginx/ssl/todolist.csr -signkey nginx/ssl/todolist.key -out nginx/ssl/todolist.crt -extensions v3_req -extfile <(
cat <<EOF
[v3_req]
keyUsage = keyEncipherment, dataEncipherment
extendedKeyUsage = serverAuth
subjectAltName = @alt_names

[alt_names]
DNS.1 = api.todolist.local
DNS.2 = todolist-api.local
DNS.3 = todolist.local
DNS.4 = localhost
IP.1 = 127.0.0.1
EOF
)

# Clean up CSR file
rm nginx/ssl/todolist.csr

# Set proper permissions
chmod 600 nginx/ssl/todolist.key
chmod 644 nginx/ssl/todolist.crt

echo "✅ SSL certificates generated successfully!"
echo ""
echo "Files created:"
echo "  - nginx/ssl/todolist.key (private key)"
echo "  - nginx/ssl/todolist.crt (certificate)"
echo ""
echo "You can now access the API with HTTPS:"
echo "  - https://api.todolist.local"
echo "  - https://todolist-api.local"
echo ""
echo "Note: You'll need to accept the self-signed certificate in your browser."