-- Stage 5: support stable keyset pagination for large tenant catalogs.
-- The primary key already protects tenant/entity/record identity; this index
-- makes descending created_at + record_id scans selective per tenant/entity.
create index if not exists idx_app_data_tenant_entity_created_record
    on public.app_data (tenant_id, entity, created_at desc, record_id desc);

-- Common category filtering in the catalog. Keep this partial to rows that
-- actually expose a category in the JSON payload.
create index if not exists idx_app_data_tenant_entity_category
    on public.app_data (tenant_id, entity, ((payload ->> 'category')))
    where (payload ->> 'category') is not null;


-- RLS-aware aggregation primitive. SECURITY INVOKER is intentional: the
-- caller's authenticated RLS policies on app_data remain in force.
create or replace function public.app_data_group_count(p_entity text, p_field text)
returns table(value text, count bigint)
language sql
stable
security invoker
set search_path = public
as $$
    select coalesce(a.payload ->> p_field, ''), count(*)::bigint
    from public.app_data as a
    where a.entity = p_entity
    group by a.payload ->> p_field
    order by count(*) desc, coalesce(a.payload ->> p_field, '');
$$;

revoke all on function public.app_data_group_count(text, text) from public;
grant execute on function public.app_data_group_count(text, text) to authenticated;


-- Dashboard aggregation primitive. Returns bounded metrics and the top low-stock
-- products without materializing the tenant's full catalog in Python.
create or replace function public.app_data_dashboard_summary()
returns jsonb
language sql
stable
security invoker
set search_path = public
as $$
with base as (
    select entity, payload
    from public.app_data
    where entity in ('products','leads','orders','content_plan')
),
products as (
    select count(*)::bigint as total,
           count(*) filter (where coalesce(nullif(payload->>'stock','')::numeric, 0) <= 2)::bigint as low_stock
    from base where entity = 'products'
),
leads as (
    select count(*)::bigint as total
    from base where entity = 'leads'
),
orders as (
    select count(*)::bigint as total,
           count(*) filter (where payload->>'status' in ('Новая','Связались','Ожидает оплаты','Оплачен','Собирается','Отправлен'))::bigint as active,
           count(*) filter (where payload->>'status' = 'Завершён')::bigint as completed,
           count(*) filter (where payload->>'status' = 'Отменён')::bigint as cancelled,
           coalesce(sum(nullif(replace(replace(payload->>'amount',' ',''),'₽',''), '')::numeric)
                    filter (where payload->>'status' <> 'Отменён'), 0)::numeric as amount
    from base where entity = 'orders'
),
content as (
    select count(*)::bigint as total,
           count(*) filter (where payload->>'status' = 'На проверке')::bigint as review,
           count(*) filter (
             where coalesce(payload->>'status','Идея') <> 'Опубликовано'
               and nullif(payload->>'date','') is not null
               and (payload->>'date')::date < current_date
           )::bigint as overdue,
           count(*) filter (
             where coalesce(payload->>'status','Идея') <> 'Опубликовано'
               and nullif(payload->>'date','') is not null
               and (payload->>'date')::date = current_date
           )::bigint as due_today
    from base where entity = 'content_plan'
),
low_rows as (
    select coalesce(payload->>'name','Товар') as name,
           coalesce(payload->>'brand','') as brand,
           coalesce(nullif(payload->>'stock','')::numeric,0) as stock
    from base
    where entity = 'products'
      and coalesce(nullif(payload->>'stock','')::numeric,0) <= 2
    order by coalesce(nullif(payload->>'stock','')::numeric,0), coalesce(payload->>'name','')
    limit 8
)
select jsonb_build_object(
    'products', (select row_to_json(products)::jsonb from products),
    'leads', (select row_to_json(leads)::jsonb from leads),
    'orders', (select row_to_json(orders)::jsonb from orders),
    'content', (select row_to_json(content)::jsonb from content),
    'low_stock_products', coalesce((select jsonb_agg(row_to_json(low_rows)::jsonb) from low_rows), '[]'::jsonb)
);
$$;

revoke all on function public.app_data_dashboard_summary() from public;
grant execute on function public.app_data_dashboard_summary() to authenticated;
