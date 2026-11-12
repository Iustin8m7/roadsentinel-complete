-- Guard identity with metadata.json first. Restores previous ownership only; may restore the old login failure.
BEGIN;
ALTER FUNCTION public.rs_auth_find_invitation_tenant(text) OWNER TO "rsint_app_261110b__lookup";
ALTER FUNCTION public.rs_auth_find_refresh_tenant(text) OWNER TO "rsint_app_261110b__lookup";
ALTER FUNCTION public.rs_auth_find_user(text) OWNER TO "rsint_app_261110b__lookup";
ALTER FUNCTION public.rs_platform_tenant() OWNER TO "rsint_app_261110b__lookup";
ALTER FUNCTION public.rs_resource_tenant(text,uuid) OWNER TO "rsint_app_261110b__lookup";
ALTER FUNCTION public.rs_tenant_id_by_slug(text) OWNER TO "rsint_app_261110b__lookup";
COMMIT;
