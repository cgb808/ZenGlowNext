# Nginx Dockerfile for ZenGlow
FROM ubuntu:22.04

# Install build dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    libpcre3-dev \
    libssl-dev \
    zlib1g-dev \
    libgeoip-dev \
    libxml2-dev \
    libxslt1-dev \
    libgd-dev \
    wget \
    curl \
    openssl \
    && rm -rf /var/lib/apt/lists/*

# Create nginx user
RUN useradd --system --home /var/cache/nginx --shell /sbin/nologin --comment "nginx user" --user-group nginx

# Copy nginx source
COPY . /usr/src/nginx/
WORKDIR /usr/src/nginx

# Configure and compile nginx with modules for ZenGlow
RUN ./configure \
    --prefix=/etc/nginx \
    --sbin-path=/usr/sbin/nginx \
    --conf-path=/etc/nginx/nginx.conf \
    --error-log-path=/var/log/nginx/error.log \
    --http-log-path=/var/log/nginx/access.log \
    --pid-path=/var/run/nginx.pid \
    --lock-path=/var/run/nginx.lock \
    --http-client-body-temp-path=/var/cache/nginx/client_temp \
    --http-proxy-temp-path=/var/cache/nginx/proxy_temp \
    --http-fastcgi-temp-path=/var/cache/nginx/fastcgi_temp \
    --http-uwsgi-temp-path=/var/cache/nginx/uwsgi_temp \
    --http-scgi-temp-path=/var/cache/nginx/scgi_temp \
    --user=nginx \
    --group=nginx \
    --with-http_ssl_module \
    --with-http_realip_module \
    --with-http_addition_module \
    --with-http_sub_module \
    --with-http_dav_module \
    --with-http_flv_module \
    --with-http_mp4_module \
    --with-http_gunzip_module \
    --with-http_gzip_static_module \
    --with-http_random_index_module \
    --with-http_secure_link_module \
    --with-http_stub_status_module \
    --with-http_auth_request_module \
    --with-http_xslt_module=dynamic \
    --with-http_image_filter_module=dynamic \
    --with-http_geoip_module=dynamic \
    --with-threads \
    --with-stream \
    --with-stream_ssl_module \
    --with-stream_realip_module \
    --with-stream_geoip_module=dynamic \
    --with-http_slice_module \
    --with-http_v2_module \
    --with-http_v3_module \
    --with-file-aio \
    --with-http_secure_link_module

# Compile nginx
RUN make && make install

# Create nginx directories and cleanup in one step
RUN mkdir -p /var/cache/nginx/client_temp \
    /var/cache/nginx/proxy_temp \
    /var/cache/nginx/fastcgi_temp \
    /var/cache/nginx/uwsgi_temp \
    /var/cache/nginx/scgi_temp \
    /var/log/nginx \
    /data/up1 \
    /data/images \
    && chown -R nginx:nginx /var/cache/nginx /var/log/nginx /data \
    && cd / \
    && rm -rf /usr/src/nginx

# Create web root for ZenGlow
RUN mkdir -p /var/www/zenglow && chown -R nginx:nginx /var/www/zenglow

# Copy nginx configuration
COPY nginx.conf /etc/nginx/nginx.conf
# Remove any default config files that might conflict
RUN rm -f /etc/nginx/conf.d/default.conf /etc/nginx/conf.d/nginx.conf /etc/nginx/nginx.conf.default

# Generate self-signed SSL certificate for development
RUN mkdir -p /etc/nginx/ssl && \
    openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
    -keyout /etc/nginx/ssl/zenglow.key \
    -out /etc/nginx/ssl/zenglow.crt \
    -subj "/C=US/ST=CA/L=SF/O=ZenGlow/OU=Dev/CN=zenglow.local"

# Create simple index.html for proxied server
RUN echo '<!DOCTYPE html><html><head><title>ZenGlow Proxied Server</title></head><body><h1>ZenGlow Proxy Server Working!</h1><p>This content is served from the proxied server on port 8080.</p><p>Images are served directly from /data/images directory.</p></body></html>' > /data/up1/index.html

# Clean up build dependencies
RUN apt-get purge -y build-essential && apt-get autoremove -y

# Forward request and error logs to docker log collector
RUN ln -sf /dev/stdout /var/log/nginx/access.log \
    && ln -sf /dev/stderr /var/log/nginx/error.log

# Expose ports
EXPOSE 80 443

# Health check
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
    CMD curl -f http://localhost/health || exit 1

# Start nginx
CMD ["nginx", "-g", "daemon off;"]
