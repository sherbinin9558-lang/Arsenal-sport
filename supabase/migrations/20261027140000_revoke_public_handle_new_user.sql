-- A trigger function should not be callable as a public PostgREST RPC.
-- Revoking EXECUTE does not disable an already-installed trigger: PostgreSQL
-- checks trigger-function privileges when CREATE TRIGGER is executed, not
-- for each row processed by the trigger.
--
-- Keep the function SECURITY DEFINER for its registration workflow, but
-- remove direct execution rights from API-facing roles. The function's
-- existing empty search_path and schema-qualified object references remain
-- important security controls.
revoke all on function public.handle_new_user()
    from public, anon, authenticated;
