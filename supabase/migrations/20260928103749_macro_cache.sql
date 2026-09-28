create table if not exists public.macro_observations (
    series text not null,
    as_of date not null,
    value double precision not null,
    source text not null default 'fred',
    fetched_at timestamptz not null default now(),
    constraint macro_observations_pkey primary key (series, as_of)
);

alter table public.macro_observations enable row level security;

create index if not exists macro_observations_series_as_of_idx
    on public.macro_observations (series, as_of desc);

create or replace view public.macro_latest as
select distinct on (series)
    series,
    as_of,
    value,
    source,
    fetched_at
from public.macro_observations
order by series, as_of desc;
