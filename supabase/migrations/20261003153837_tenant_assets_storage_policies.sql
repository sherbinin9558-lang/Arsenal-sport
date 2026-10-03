-- Tenant file storage (private bucket "tenant-assets").
-- Objects live under <tenant_id>/<file>; access follows tenant membership.
insert into storage.buckets (id, name, public, file_size_limit, allowed_mime_types)
values ('tenant-assets', 'tenant-assets', false, 15728640,
        array['image/png','image/jpeg','image/webp'])
on conflict (id) do nothing;

create or replace function public.storage_object_tenant(object_name text)
returns uuid
language sql
immutable
set search_path = public
as $$
  select case
    when split_part(object_name, '/', 1) ~* '^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$'
    then split_part(object_name, '/', 1)::uuid
  end;
$$;

revoke all on function public.storage_object_tenant(text) from public;
grant execute on function public.storage_object_tenant(text) to authenticated;
-- Supabase grants new functions to anon by default; revoke it explicitly.
revoke execute on function public.storage_object_tenant(text) from anon;
revoke execute on function public.is_tenant_writer(uuid) from anon;

drop policy if exists "tenant members can read assets" on storage.objects;
create policy "tenant members can read assets" on storage.objects
for select to authenticated
using (
  bucket_id = 'tenant-assets'
  and public.is_tenant_member(public.storage_object_tenant(name))
);

drop policy if exists "tenant writers can upload assets" on storage.objects;
create policy "tenant writers can upload assets" on storage.objects
for insert to authenticated
with check (
  bucket_id = 'tenant-assets'
  and public.is_tenant_writer(public.storage_object_tenant(name))
);

drop policy if exists "tenant writers can update assets" on storage.objects;
create policy "tenant writers can update assets" on storage.objects
for update to authenticated
using (
  bucket_id = 'tenant-assets'
  and public.is_tenant_writer(public.storage_object_tenant(name))
)
with check (
  bucket_id = 'tenant-assets'
  and public.is_tenant_writer(public.storage_object_tenant(name))
);

drop policy if exists "tenant writers can delete assets" on storage.objects;
create policy "tenant writers can delete assets" on storage.objects
for delete to authenticated
using (
  bucket_id = 'tenant-assets'
  and public.is_tenant_writer(public.storage_object_tenant(name))
);
