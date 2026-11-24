-- Run as the project's postgres role on a dedicated Medora Supabase project.
-- Substitute medora_demo consistently for a separate synthetic demo project.
-- Set each LOGIN password securely with psql \password, outside this file.
CREATE ROLE medora_migrator LOGIN;
CREATE ROLE medora_runtime LOGIN;
GRANT medora_migrator TO postgres;
GRANT CONNECT ON DATABASE postgres TO medora_migrator, medora_runtime;
CREATE SCHEMA medora AUTHORIZATION medora_migrator;
REVOKE ALL ON SCHEMA medora FROM PUBLIC, anon, authenticated;
GRANT USAGE ON SCHEMA medora TO medora_runtime;

ALTER DEFAULT PRIVILEGES FOR ROLE medora_migrator IN SCHEMA medora
  GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO medora_runtime;
ALTER DEFAULT PRIVILEGES FOR ROLE medora_migrator IN SCHEMA medora
  GRANT USAGE, SELECT ON SEQUENCES TO medora_runtime;

-- Run the following as medora_migrator after Django migrations.
-- REVOKE INSERT, UPDATE, DELETE ON medora.django_migrations FROM medora_runtime;
-- REVOKE UPDATE, DELETE ON medora.audit_auditlog FROM medora_runtime;
