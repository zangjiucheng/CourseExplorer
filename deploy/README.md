# Deploying uw-course to oracle-cloud

The server (`oracle-cloud`, Ubuntu 24.04, ~1 GB RAM, no swap) is too small to
build the frontend in place, so the image is built in GitHub Actions and pulled
here. This slots into the existing "container on `127.0.0.1:<port>` + nginx TLS"
pattern already used by beanbook/hedgedoc/metar.

## One-time prerequisites

1. **Build the image** — push a `v*` tag (or run the *Publish Docker image*
   workflow manually). It publishes `ghcr.io/zangjiucheng/uw-course:latest`.
2. **Make the ghcr package public** (or configure `docker login ghcr.io` on the
   server with a read PAT). GitHub → Packages → uw-course → Package settings →
   Change visibility → Public. Matches the existing public `ghcr.io/zangjiucheng/*`
   images.
3. **DNS** — add an A record `course.jiucheng-zang.ca → 40.233.67.184`.
4. **MongoDB** — (optional hardening) create an Atlas user with role
   `read` on `UWRegistrationDB` only, and put its URI in `.env` (below).

## Deploy

```bash
# on oracle-cloud
mkdir -p ~/uw-course && cd ~/uw-course
# copy deploy/docker-compose.yml here (scp or git)

# optional: scoped read-only Mongo URI (else the baked-in default is used)
printf 'MONGODB_URI=%s\n' 'mongodb+srv://.../?retryWrites=true&w=majority' > .env

docker compose pull
docker compose up -d
curl -s localhost:31415/api/terms | head   # sanity check
```

## nginx + TLS

```bash
sudo cp nginx-course.conf /etc/nginx/sites-available/course.jiucheng-zang.ca
sudo ln -s /etc/nginx/sites-available/course.jiucheng-zang.ca /etc/nginx/sites-enabled/
sudo nginx -t
sudo certbot --nginx -d course.jiucheng-zang.ca   # fills in 443/ssl + http->https redirect
sudo systemctl reload nginx
```

## Updating

```bash
cd ~/uw-course && docker compose pull && docker compose up -d
```
