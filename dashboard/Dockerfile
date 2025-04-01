FROM nginx

# Copy built frontend files
COPY . /usr/share/nginx/html

# Replace the default Nginx config with your own
COPY nginx.conf /etc/nginx/conf.d/default.conf
