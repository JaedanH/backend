-- Enable pgcrypto extension for UUID generation
CREATE EXTENSION IF NOT EXISTS pgcrypto;

-- Schema definition for the EthixAI companies table

CREATE TABLE IF NOT EXISTS public.companies (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  name text NOT NULL,
  ticker text,
  ethics_score int,
  source_reason text,
  last_updated timestamptz DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_companies_name ON public.companies (name);
