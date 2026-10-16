-- Tenant-scoped dashboard aggregation for ShopPilot AI.
-- SECURITY INVOKER preserves caller privileges and the database RLS context.
CREATE OR REPLACE FUNCTION public.app_data_dashboard_summary(p_tenant_id uuid)
RETURNS jsonb
LANGUAGE plpgsql
SECURITY INVOKER
SET search_path = ''
AS $function$
DECLARE
  v_products_total bigint := 0;
  v_products_low bigint := 0;
  v_leads_total bigint := 0;
  v_orders_total bigint := 0;
  v_orders_active bigint := 0;
  v_orders_completed bigint := 0;
  v_orders_cancelled bigint := 0;
  v_orders_amount numeric := 0;
  v_content_total bigint := 0;
  v_content_review bigint := 0;
  v_content_overdue bigint := 0;
  v_content_due_today bigint := 0;
  v_low_stock_products jsonb := '[]'::jsonb;
BEGIN
  IF auth.uid() IS NULL THEN
    RAISE EXCEPTION 'AUTH_REQUIRED' USING ERRCODE = '42501';
  END IF;
  IF p_tenant_id IS NULL OR NOT private.is_tenant_member(p_tenant_id) THEN
    RAISE EXCEPTION 'NOT_AUTHORIZED' USING ERRCODE = '42501';
  END IF;
  WITH products AS (
    SELECT record_id, payload,
      CASE WHEN regexp_replace(coalesce(payload->>'stock', ''), '[^0-9.-]', '', 'g') ~ '^-?[0-9]+(\.[0-9]+)?$'
        THEN regexp_replace(coalesce(payload->>'stock', ''), '[^0-9.-]', '', 'g')::numeric
        ELSE NULL END AS stock_value
    FROM public.app_data WHERE tenant_id = p_tenant_id AND entity = 'products'
  )
  SELECT count(*), count(*) FILTER (WHERE stock_value <= 2),
    coalesce(jsonb_agg(payload || jsonb_build_object('record_id', record_id)
      ORDER BY stock_value ASC, coalesce(payload->>'name', '') ASC)
      FILTER (WHERE stock_value <= 2), '[]'::jsonb)
  INTO v_products_total, v_products_low, v_low_stock_products FROM products;
  SELECT count(*) INTO v_leads_total FROM public.app_data WHERE tenant_id = p_tenant_id AND entity = 'leads';
  WITH orders AS (
    SELECT payload,
      CASE WHEN regexp_replace(replace(coalesce(payload->>'amount', ''), ',', '.'), '[^0-9.-]', '', 'g') ~ '^-?[0-9]+(\.[0-9]+)?$'
        THEN regexp_replace(replace(coalesce(payload->>'amount', ''), ',', '.'), '[^0-9.-]', '', 'g')::numeric
        ELSE 0 END AS amount_value
    FROM public.app_data WHERE tenant_id = p_tenant_id AND entity = 'orders'
  )
  SELECT count(*), count(*) FILTER (WHERE payload->>'status' IN ('Новая','Связались','Ожидает оплаты','Оплачен','Собирается','Отправлен')),
    count(*) FILTER (WHERE payload->>'status' = 'Завершён'),
    count(*) FILTER (WHERE payload->>'status' = 'Отменён'),
    coalesce(sum(amount_value) FILTER (WHERE coalesce(payload->>'status','') <> 'Отменён'), 0)
  INTO v_orders_total, v_orders_active, v_orders_completed, v_orders_cancelled, v_orders_amount FROM orders;
  WITH content_rows AS (
    SELECT payload, CASE WHEN coalesce(payload->>'date','') ~ '^\d{4}-\d{2}-\d{2}$' THEN (payload->>'date')::date ELSE NULL END AS due_date
    FROM public.app_data WHERE tenant_id = p_tenant_id AND entity = 'content_plan'
  )
  SELECT count(*), count(*) FILTER (WHERE payload->>'status' = 'На проверке'),
    count(*) FILTER (WHERE coalesce(payload->>'status','') <> 'Опубликовано' AND due_date < CURRENT_DATE),
    count(*) FILTER (WHERE coalesce(payload->>'status','') <> 'Опубликовано' AND due_date = CURRENT_DATE)
  INTO v_content_total, v_content_review, v_content_overdue, v_content_due_today FROM content_rows;
  RETURN jsonb_build_object(
    'products', jsonb_build_object('total', v_products_total, 'low_stock', v_products_low),
    'leads', jsonb_build_object('total', v_leads_total),
    'orders', jsonb_build_object('total', v_orders_total, 'active', v_orders_active, 'completed', v_orders_completed, 'cancelled', v_orders_cancelled, 'amount', v_orders_amount),
    'content', jsonb_build_object('total', v_content_total, 'review', v_content_review, 'overdue', v_content_overdue, 'due_today', v_content_due_today),
    'low_stock_products', v_low_stock_products
  );
END;
$function$;
REVOKE ALL ON FUNCTION public.app_data_dashboard_summary(uuid) FROM PUBLIC, anon;
GRANT EXECUTE ON FUNCTION public.app_data_dashboard_summary(uuid) TO authenticated;
