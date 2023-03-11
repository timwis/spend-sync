alter table "public"."accounts" drop column "truelayer_account_id";

alter table "public"."accounts" drop column "truelayer_display_name";

alter table "public"."accounts" add column "display_name" text not null;

alter table "public"."accounts" add column "external_account_id" text not null;

alter table "public"."connections" add column "provider" text not null;

create or replace view "public"."decrypted_connections" as  SELECT connections.id,
    connections.created_at,
    connections.user_id,
    connections.access_token,
        CASE
            WHEN (connections.access_token IS NULL) THEN NULL::text
            ELSE
            CASE
                WHEN (connections.key_id IS NULL) THEN NULL::text
                ELSE convert_from(pgsodium.crypto_aead_det_decrypt(decode(connections.access_token, 'base64'::text), convert_to((connections.id)::text, 'utf8'::name), connections.key_id, NULL::bytea), 'utf8'::name)
            END
        END AS decrypted_access_token,
    connections.expires_at,
    connections.refresh_token,
        CASE
            WHEN (connections.refresh_token IS NULL) THEN NULL::text
            ELSE
            CASE
                WHEN (connections.key_id IS NULL) THEN NULL::text
                ELSE convert_from(pgsodium.crypto_aead_det_decrypt(decode(connections.refresh_token, 'base64'::text), convert_to((connections.id)::text, 'utf8'::name), connections.key_id, NULL::bytea), 'utf8'::name)
            END
        END AS decrypted_refresh_token,
    connections.key_id,
    connections.provider
   FROM connections;



