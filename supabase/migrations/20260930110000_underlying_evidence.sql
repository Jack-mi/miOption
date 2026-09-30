create table if not exists public.underlying_evidence (
    id bigint generated always as identity primary key,
    ticker text not null check (ticker ~ '^US\.[A-Z0-9.]+$'),
    category text not null check (category in ('company', 'fundamentals', 'filing', 'earnings')),
    item_key text not null,
    source text not null,
    source_at timestamptz not null,
    fetched_at timestamptz not null,
    quality text not null check (quality in ('verified', 'legacy_unverified')),
    payload jsonb not null,
    digest text not null check (digest ~ '^[0-9a-f]{64}$'),
    inserted_at timestamptz not null default now(),
    unique (ticker, category, item_key, source, digest)
);
create index if not exists underlying_evidence_lookup
    on public.underlying_evidence (ticker, category, source_at desc, id desc);

create table if not exists public.underlying_refresh (
    ticker text not null check (ticker ~ '^US\.[A-Z0-9.]+$'),
    category text not null check (category in ('company', 'fundamentals', 'filing', 'earnings')),
    last_attempt timestamptz not null,
    last_success timestamptz,
    last_error text,
    primary key (ticker, category)
);

create table if not exists public.research_archive (
    id bigint generated always as identity primary key,
    kind text not null,
    ticker text,
    origin text not null,
    digest text not null check (digest ~ '^[0-9a-f]{64}$'),
    observed_at timestamptz,
    quality text not null check (quality in ('verified', 'legacy_unverified')),
    environment text not null check (environment in ('live', 'mock', 'unknown')),
    payload jsonb,
    inserted_at timestamptz not null default now(),
    unique (kind, origin, digest)
);

create table if not exists public.macro_refresh_state (
    series text primary key,
    last_attempt timestamptz not null,
    last_success timestamptz,
    last_error text
);

alter table public.underlying_evidence enable row level security;
alter table public.underlying_refresh enable row level security;
alter table public.research_archive enable row level security;
alter table public.macro_refresh_state enable row level security;
alter view public.macro_latest set (security_invoker = true);
revoke all on public.macro_observations, public.macro_latest from anon, authenticated;
revoke all on public.macro_refresh_state from anon, authenticated;
grant select, insert, update on public.macro_refresh_state to service_role;
revoke all on public.underlying_evidence, public.underlying_refresh, public.research_archive from anon, authenticated;
revoke all on sequence public.underlying_evidence_id_seq, public.research_archive_id_seq from anon, authenticated;
grant select, insert on public.underlying_evidence, public.research_archive to service_role;
grant select, insert, update on public.underlying_refresh to service_role;
grant usage on sequence public.underlying_evidence_id_seq, public.research_archive_id_seq to service_role;

create or replace function public.save_underlying_evidence(
    input_ticker text, input_category text, input_records jsonb, input_error text default null
) returns void language plpgsql security invoker set search_path = '' as $$
declare
    record jsonb;
    saved boolean := false;
begin
    if input_ticker !~ '^US\.[A-Z0-9.]+$' or input_category not in
        ('company', 'fundamentals', 'filing', 'earnings') or jsonb_typeof(input_records) != 'array' then
        raise exception 'invalid evidence request';
    end if;
    for record in select value from jsonb_array_elements(input_records)
    loop
        if record->>'source' not in ('edgar', 'nasdaq', 'finnhub') then
            raise exception 'source not permitted for remote evidence';
        end if;
        insert into public.underlying_evidence
            (ticker, category, item_key, source, source_at, fetched_at, quality, payload, digest)
        values (input_ticker, input_category, record->>'item_key', record->>'source',
                (record->>'source_at')::timestamptz, (record->>'fetched_at')::timestamptz,
                record->>'quality', record->'payload', record->>'digest')
        on conflict (ticker, category, item_key, source, digest) do nothing;
        saved := true;
    end loop;
    insert into public.underlying_refresh (ticker, category, last_attempt, last_success, last_error)
    values (input_ticker, input_category, now(), case when saved then now() else null end,
            left(input_error, 300))
    on conflict (ticker, category) do update
    set last_attempt = excluded.last_attempt,
        last_success = coalesce(excluded.last_success, public.underlying_refresh.last_success),
        last_error = excluded.last_error;
end;
$$;
revoke all on function public.save_underlying_evidence(text, text, jsonb, text) from public, anon, authenticated;
grant execute on function public.save_underlying_evidence(text, text, jsonb, text) to service_role;
