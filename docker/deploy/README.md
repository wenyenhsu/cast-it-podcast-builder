# Staging / production Compose stacks

These files are **not** needed for local development. Day-to-day work uses the
repo-root files:

- `docker-compose.yml`
- `docker-compose.host-access.yml` (optional: expose db/redis to the host)

## Staging

```bash
cp docker/deploy/.env.staging.example docker/deploy/.env.staging
# edit secrets in docker/deploy/.env.staging

docker compose \
  -f docker/deploy/docker-compose.staging.yml \
  --env-file docker/deploy/.env.staging \
  up --build -d
```

## Production

```bash
cp docker/deploy/.env.production.example docker/deploy/.env.production
# edit secrets in docker/deploy/.env.production

docker compose \
  -f docker/deploy/docker-compose.prod.yml \
  --env-file docker/deploy/.env.production \
  up -d
```

Do not commit `docker/deploy/.env.staging` or `docker/deploy/.env.production`.
