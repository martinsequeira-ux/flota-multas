-- =====================================================================
-- FASE 1 — Esquema de control de multas de la flota
-- DEPLOYADO en proyecto Supabase `lusqtoff-patio` (cadqikcbppxezlqzdxet)
-- Tablas namespaced con prefijo mlt_ para no colisionar con YMS.
-- =====================================================================

create table if not exists public.mlt_vehiculos (
    id          bigint generated always as identity primary key,
    patente     text        not null unique,
    marca       text,
    modelo      text,
    created_at  timestamptz not null default now()
);

create table if not exists public.mlt_multas (
    id                bigint        generated always as identity primary key,
    vehiculo_id       bigint        not null references public.mlt_vehiculos(id) on delete cascade,
    acta              text          not null unique,
    monto             numeric(12,2) not null default 0,
    fecha_infraccion  date,
    estado            text          not null default 'pendiente'
                      check (estado in ('pendiente','pagada','en_gestion','prescripta','no_aplica')),
    created_at        timestamptz   not null default now(),
    updated_at        timestamptz   not null default now()
);

create index if not exists idx_mlt_multas_vehiculo on public.mlt_multas(vehiculo_id);
create index if not exists idx_mlt_multas_estado   on public.mlt_multas(estado);

create or replace function public.mlt_set_updated_at()
returns trigger
language plpgsql
set search_path = ''
as $$
begin
    new.updated_at = now();
    return new;
end;
$$;

drop trigger if exists trg_mlt_multas_updated_at on public.mlt_multas;
create trigger trg_mlt_multas_updated_at
    before update on public.mlt_multas
    for each row execute function public.mlt_set_updated_at();

-- RLS: panel (anon) solo lee; el scraper escribe con service_role (bypassa RLS)
alter table public.mlt_vehiculos enable row level security;
alter table public.mlt_multas    enable row level security;

drop policy if exists "mlt_lectura_anon_vehiculos" on public.mlt_vehiculos;
create policy "mlt_lectura_anon_vehiculos" on public.mlt_vehiculos
    for select to anon using (true);

drop policy if exists "mlt_lectura_anon_multas" on public.mlt_multas;
create policy "mlt_lectura_anon_multas" on public.mlt_multas
    for select to anon using (true);

-- Cargá acá tus 40 patentes reales (ejemplo):
insert into public.mlt_vehiculos (patente, marca, modelo) values
    ('AA123BB','Volkswagen','Amarok'),
    ('AC456DD','Ford','Ranger'),
    ('AD789EF','Toyota','Hilux'),
    ('AE012GH','Fiat','Toro')
on conflict (patente) do nothing;
