create or replace function public.record_macro_refresh(input_rows jsonb)
returns void language plpgsql security invoker set search_path = '' as $$
declare
    entry jsonb;
begin
    if jsonb_typeof(input_rows) != 'array' then
        raise exception 'invalid refresh state';
    end if;
    for entry in select value from jsonb_array_elements(input_rows)
    loop
        insert into public.macro_refresh_state (series, last_attempt, last_success, last_error)
        values (entry->>'series', (entry->>'last_attempt')::timestamptz,
                (entry->>'last_success')::timestamptz, entry->>'last_error')
        on conflict (series) do update
        set last_attempt = excluded.last_attempt,
            last_success = coalesce(excluded.last_success, public.macro_refresh_state.last_success),
            last_error = excluded.last_error;
    end loop;
end;
$$;
revoke all on function public.record_macro_refresh(jsonb) from public, anon, authenticated;
grant execute on function public.record_macro_refresh(jsonb) to service_role;
