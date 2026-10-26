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
- Prod images built/tagged on the source machine — **validation only**, not needed
  for the server (it builds its own from source, §3). Confirms the merged
  backend + frontend build cleanly:
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

This is the **recommended, simplest path** — checkout the source and build right
here; no image transfer involved. `docker-compose.prod.yml` only **pulls**
`ghcr.io/securo-finance/*:latest` (upstream's build, no Akahu), so build our
branch under the same tags so compose resolves to our images:

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

> The `3000` above is the published frontend port, not a fixed number: on this
> server it is `3010` (3000 belongs to `netbootxyz`) and the proxy is an nginx
> container rather than Caddy. See §8 for the setup that is actually running.

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

## 8. Updating the running deployment (what the server actually does)

The server does **not** run `docker-compose.prod.yml`. It runs
`docker-compose.yml` (the dev compose) from `/home/homeserveruser/docker/securo`:
the backend bind-mounts `./backend` at `/app` and runs
`alembic upgrade head && uvicorn --reload`, the frontend is the vite dev server,
and the reverse proxy is an nginx container (`/etc/nginx/conf.d/money.conf`),
not Caddy.

Consequences that matter:

- `FRONTEND_PORT=3010`, because host port 3000 is already taken by `netbootxyz`
  on this machine. Whatever proxies `money.hmg.co.nz` must target 3010 (or
  whichever `FRONTEND_PORT` says), never a hard-coded 3000.
- `BACKEND_PORT=127.0.0.1:8000` keeps the API off the LAN.
- `--reload` picks up changed Python files but **alembic only runs when the
  container starts**. A `git pull` therefore ships new code against the old
  schema unless the migration is run by hand.

Updating:

```bash
cd /home/homeserveruser/docker/securo
git fetch && git checkout feat/akahu-provider && git pull

# 1. always, after a pull that touches migrations:
docker compose exec db pg_dump -U postgres -d securo -Fc > pre-update-$(date +%F).dump
docker compose exec backend alembic upgrade head

# 2. celery has no --reload, so it keeps the old code until restarted:
docker compose restart celery-worker celery-beat

# 3. if package.json/package-lock.json changed (node_modules is a named volume):
docker compose exec frontend npm ci
```

Skipping the alembic step is the failure mode seen on 2026-10-26: code at
`098`, database at `084`, and every query touching a new column failed with

    asyncpg.exceptions.UndefinedColumnError: column workspaces.timezone does not exist

which the UI reports as empty pages and 500s. The rows were never lost; the
schema was simply behind the code. Check the version explicitly:

```bash
docker compose exec db psql -U postgres -d securo -tAc "select version_num from alembic_version;"
docker compose exec backend alembic heads
```

### Re-fetching one account's history

The sync window is anchored on `bank_connections.last_sync_at`, which one
connection shares across all of its accounts, so a SQL-only datafix cannot name
a single account. The repair that works on the shipped code is to clear the
account's rows and let the sync see an account with no history, which makes it
ask for everything:

```sql
-- snapshot first; the provider will return the same rows again
create table _backfill_backup as
select t.* from transactions t
join accounts a on a.id = t.account_id
join institutions i on i.id = a.institution_id
where i.name = 'Kiwibank';

delete from transactions t
using accounts a, institutions i
where t.account_id = a.id and a.institution_id = i.id and i.name = 'Kiwibank';
```

Then trigger a sync of that connection (`docker compose exec celery-worker python -c
"from app.tasks.sync_tasks import sync_single_connection;
sync_single_connection.delay('<connection_id>', '<user_id>')"`). Other accounts
keep the incremental window, so only the cleared one is re-read in full. The
synthetic `opening_balance` rows are recomputed on that same pass.

Do this only for accounts with no user state on the rows (no category, notes,
tags, ignored flag or transfer link), because deleting them discards it.

## 9. Verify

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
