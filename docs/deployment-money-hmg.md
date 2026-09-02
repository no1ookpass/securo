# Deployment runbook — money.hmg.co.nz

Migrating the local Securo instance (branch `feat/akahu-provider`) to a home
server exposed as `https://money.hmg.co.nz`.

## Status of local prep (already done 2026-09-02)

- Branch `feat/akahu-provider` pushed to fork `https://github.com/no1ookpass/securo.git`.
- Local DB reconciled to merged schema (institutions + `institution_id`, `alembic_version=084`).
- Backups (on the machine where Securo currently runs):
  `/home/ashley/dev/securo/backups/securo-migration-2026-09-02/`
  - `securo-pgdata-2026-09-02.dump` — `pg_dump -Fc` of the whole DB (users, workspace, categories, accounts, connections, transactions, settings, migration version).
  - `env-backup-2026-09-02` — the production `.env` (contains `SECRET_KEY`, Akahu tokens are encrypted with it — must be preserved verbatim).
  - `securo_*.tar.gz` — attachments / agent_knowledge / embedding_models volumes (all currently **empty**; kept for completeness).
- Prod images built/tagged on the source machine:
  - `ghcr.io/securo-finance/securo-backend:latest` (covers backend + celery-worker + celery-beat + mcp-server)
  - `ghcr.io/securo-finance/securo-frontend:latest` (nginx static build)

## 1. Server prerequisites

```bash
# docker + compose plugin
curl -fsSL https://get.docker.com | sh
sudo systemctl enable --now docker

# git (for cloning) and caddy (for TLS)
sudo apt-get install -y git caddy
```

## 2. Get the code onto the server

```bash
git clone https://github.com/no1ookpass/securo.git
cd securo
git fetch origin
git checkout feat/akahu-provider
```

> Keep this checkout permanently — the prod compose file lives here and reads
> `.env` from this directory.

## 3. Build the images on the server

`docker-compose.prod.yml` only **pulls** `ghcr.io/securo-finance/*:latest`, which
is upstream's build (no Akahu). Build our branch under the same tags:

```bash
docker build -t ghcr.io/securo-finance/securo-backend:latest ./backend
docker build -t ghcr.io/securo-finance/securo-frontend:latest ./frontend
```

(Requires internet for `pip`/`npm`. `backend/uv.lock` is current — includes
`reportlab` for the invoice PDF feature.)

Alternative: `docker save` the prebuilt images on the source machine and
`docker load` them on the server (see §7).

## 4. Configure `.env`

Copy the backed-up `.env` onto the server as `./.env` (same dir as
`docker-compose.prod.yml`), then adjust:

```bash
cp env-backup-2026-09-02 ./.env   # preserve SECRET_KEY etc. verbatim
# then edit .env:
#   FRONTEND_URL=https://money.hmg.co.nz
#   WEBAUTHN_ORIGIN=https://money.hmg.co.nz
#   (keep AKAHU_ENABLED=true, AGENTS_ENABLED=true, COMPOSE_PROFILES=agents,
#    OPENEXCHANGERATES_APP_ID, AGENTS_OPENAI_COMPAT_* for LM Studio, etc.)
```

Never change `SECRET_KEY` — stored Akahu tokens are encrypted with it and will
be undecryptable otherwise.

## 5. Restore the database

```bash
# copy the dump to the server (scp/rsync from source machine)
scp securo-pgdata-2026-09-02.dump user@server:~

# start only the DB
docker compose -f docker-compose.prod.yml up -d db

# drop the dump into the container and restore it (fresh volume: no --clean needed)
docker cp ~/securo-pgdata-2026-09-02.dump securo-db-1:/tmp/securo.dump
docker compose -f docker-compose.prod.yml exec -T db pg_restore -U postgres -d securo /tmp/securo.dump
```

The dump already carries the reconciled schema (`institutions` table,
`accounts.institution_id`, `alembic_version=084`) — no migration step needed.
Verify:

```bash
docker compose -f docker-compose.prod.yml exec -T db psql -U postgres -d securo \
  -c "SELECT version_num FROM alembic_version;"
# expect: 084
```

The three data volumes (`attachments`, `agent_knowledge`, `agent_embedding_models`)
are empty and created automatically on first `up` — nothing to restore. If they
ever contain data, restore with: `docker run --rm -v <vol>:/data -v $PWD:/backup alpine tar xzf /backup/<vol>.tar.gz -C /data`.

## 6. DNS + HTTPS

- DNS: add an **A record** `money.hmg.co.nz` → the server's public IP.
  - Static IP: plain A record.
  - Dynamic IP: use a DDNS hostname and a CNAME, or a Cloudflare/Tailscale tunnel.
- Router: forward **TCP 80 and 443** to the server's LAN IP.
- Caddy (auto-TLS via Let's Encrypt):

```bash
sudo tee /etc/caddy/Caddyfile <<'EOF'
money.hmg.co.nz {
    reverse_proxy 127.0.0.1:3000
    encode zstd gzip
}
EOF
sudo systemctl enable --now caddy
```

## 7. Bring it up

```bash
# agents profile only if AGENTS_ENABLED=true
docker compose -f docker-compose.prod.yml up -d
# or with agents:
docker compose -f docker-compose.prod.yml --profile agents up -d

docker compose -f docker-compose.prod.yml ps
```

Service ports: backend `:8000` (internal), frontend nginx `:3000` (Caddy
upstream). The backend runs `alembic upgrade head` on boot; it's already at
head so it's a no-op.

## 8. Verify

```bash
curl -s -o /dev/null -w "%{http_code}\n" https://money.hmg.co.nz        # 200
curl -s -o /dev/null -w "%{http_code}\n" https://money.hmg.co.nz/api/health  # 200
```

- Log in with the existing user (data restored from dump).
- Accounts page: Akahu connection present, institutions populated after next
  sync (hourly Celery beat; 4h staleness threshold).
- Check `docker compose -f docker-compose.prod.yml logs backend` for errors.

## Image transfer alternative (no build on server)

```bash
# on source machine:
docker save ghcr.io/securo-finance/securo-backend:latest ghcr.io/securo-finance/securo-frontend:latest | gzip > securo-images.tar.gz
# on server:
gunzip -c securo-images.tar.gz | docker load
```

## Rollback

Keep the source machine's dev stack running as-is until the server is verified.
To revert: stop prod on the server and repoint DNS; no local data is touched
during migration.
