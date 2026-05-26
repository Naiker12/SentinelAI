# Prisma + Supabase

Prisma se usa solo para versionar y migrar el esquema de Supabase/Postgres.
El agente Python inserta eventos usando `SUPABASE_URL` y `SUPABASE_SERVICE_ROLE_KEY`.

## Variables necesarias

En `.env`:

```env
DATABASE_URL="postgres://prisma.PROJECT_REF:PRISMA_PASSWORD@REGION.pooler.supabase.com:5432/postgres"
SUPABASE_URL="https://PROJECT_REF.supabase.co"
SUPABASE_SERVICE_ROLE_KEY="SERVICE_ROLE_KEY"
SUPABASE_DETECTION_EVENTS_TABLE="detection_events"
```

`DATABASE_URL` es para Prisma migrations.
`SUPABASE_SERVICE_ROLE_KEY` es solo para backend local, nunca para frontend.

## Instalar Prisma

```powershell
npm install
```

## Crear migracion

```powershell
npx prisma migrate dev --name init_supabase_schema
npx prisma generate
```

## Ver datos

```powershell
npx prisma studio
```

## Tablas

- `camaras`: catalogo de camaras.
- `detection_events`: eventos generados por `AgentePercepcion`.

## RLS en Supabase

Como `public` es un schema expuesto por Supabase, activa RLS en las tablas antes de exponerlas a clientes frontend. El backend local puede insertar con `service_role`, que no debe salir del servidor.
