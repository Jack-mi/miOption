create or replace function public.save_underlying_evidence(
    input_ticker text, input_category text, input_records jsonb, input_error text default null
) returns void language plpgsql security invoker set search_path = '' as $$
declare
    entry jsonb;
    saved boolean := false;
begin
    if input_ticker !~ '^US\.[A-Z0-9.]+$' or input_category not in
        ('company', 'fundamentals', 'filing', 'earnings') or jsonb_typeof(input_records) != 'array' then
        raise exception 'invalid evidence request';
    end if;
    for entry in select value from jsonb_array_elements(input_records)
    loop
        if entry->>'source' not in ('edgar', 'nasdaq', 'finnhub') then
            raise exception 'source not permitted for remote evidence';
        end if;
        insert into public.underlying_evidence
            (ticker, category, item_key, source, source_at, fetched_at, quality, payload, digest)
        values (input_ticker, input_category, entry->>'item_key', entry->>'source',
                (entry->>'source_at')::timestamptz, (entry->>'fetched_at')::timestamptz,
                entry->>'quality', entry->'payload', entry->>'digest')
        on conflict (ticker, category, item_key, source, digest) do nothing;
        saved := true;
    end loop;
    insert into public.underlying_refresh (ticker, category, last_attempt, last_success, last_error)
    values (input_ticker, input_category, now(),
            case when saved and input_error is null then now() else null end,
            left(input_error, 300))
    on conflict (ticker, category) do update
    set last_attempt = excluded.last_attempt,
        last_success = coalesce(excluded.last_success, public.underlying_refresh.last_success),
        last_error = excluded.last_error;
end;
$$;
revoke all on function public.save_underlying_evidence(text, text, jsonb, text) from public, anon, authenticated;
grant execute on function public.save_underlying_evidence(text, text, jsonb, text) to service_role;
