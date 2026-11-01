# Frontend Service - Nginx serving static dashboard files
FROM nginx:alpine

# Copy dashboard files
COPY dashboard/ /usr/share/nginx/html/

# Copy nginx configuration
COPY nginx.conf /etc/nginx/conf.d/default.conf

# Expose port 80
EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
