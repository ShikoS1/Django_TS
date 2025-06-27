#!/bin/bash

NGINX_CONF="/etc/nginx/sites-available/default"

cat > "$NGINX_CONF" <<EOF
server {
    listen 80 default_server;
    listen [::]:80 default_server;

    location /static/ {
        alias /home/shiko/Django_TS/TS_equipment/static/;
        expires 30d;
        add_header Cache-Control "public, immutable";
    }

    location / {
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_pass http://127.0.0.1:8000;
    }

    client_max_body_size 20M;
    keepalive_timeout 65;
}
EOF

nginx -t && systemctl reload nginx

echo "Nginx default config обновлён и перезапущен."
