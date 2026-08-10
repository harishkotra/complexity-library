-- Complexity Library initial relational model.
-- Public reads are deliberately limited to published content; service-role API code owns writes.

create extension if not exists pgcrypto;
create extension if not exists vector;

create type public.function_status as enum ('processing', 'published', 'rejected', 'removed', 'failed');
create type public.moderation_status as enum ('pending', 'allowed', 'review', 'blocked');
create type public.interaction_type as enum ('view', 'like', 'save', 'run', 'share');

create table public.anonymous_sessions (
  id uuid primary key default gen_random_uuid(),
  token_hash text not null unique,
  user_id uuid references auth.users(id) on delete set null,
  expires_at timestamptz not null,
  created_at timestamptz not null default now(),
  claimed_at timestamptz
);

create table public.functions (
  id uuid primary key default gen_random_uuid(),
  slug text not null unique,
  title text not null check (char_length(title) between 1 and 120),
  description text,
  prompt text check (char_length(prompt) <= 1500),
  code text not null check (char_length(code) <= 20000),
  language text not null check (language in ('python', 'javascript', 'typescript')),
  normalized_code text not null,
  code_hash text not null,
  ast_fingerprint text,
  time_complexity text not null,
  space_complexity text not null,
  confidence numeric(4,3) not null check (confidence >= 0 and confidence <= 1),
  analysis jsonb not null,
  visualization_spec jsonb not null,
  pattern text not null,
  analyzer_version text not null default '1',
  anonymous_session_id uuid references public.anonymous_sessions(id) on delete set null,
  user_id uuid references auth.users(id) on delete set null,
  status public.function_status not null default 'processing',
  moderation_status public.moderation_status not null default 'pending',
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  published_at timestamptz,
  constraint functions_unique_analysis_cache unique (code_hash, analyzer_version)
);

create index functions_public_browse_idx on public.functions (status, moderation_status, published_at desc);
create index functions_filter_idx on public.functions (language, time_complexity, pattern, published_at desc);
create index functions_ast_fingerprint_idx on public.functions (ast_fingerprint) where ast_fingerprint is not null;
create index functions_search_idx on public.functions using gin (
  to_tsvector('english', coalesce(title, '') || ' ' || coalesce(description, '') || ' ' || coalesce(prompt, ''))
);

create table public.function_analyses (
  id uuid primary key default gen_random_uuid(),
  function_id uuid not null references public.functions(id) on delete cascade,
  schema_version integer not null,
  source text not null check (source in ('deterministic', 'agno_fallback', 'cached_exact', 'curated')),
  analyzer_version text not null,
  analysis jsonb not null,
  visualization_spec jsonb not null,
  created_at timestamptz not null default now()
);
create index function_analyses_function_created_idx on public.function_analyses (function_id, created_at desc);

create table public.function_embeddings (
  id uuid primary key default gen_random_uuid(),
  function_id uuid not null references public.functions(id) on delete cascade,
  embedding vector(1536) not null,
  embedding_type text not null check (embedding_type in ('normalized_code', 'description', 'prompt')),
  model text not null,
  created_at timestamptz not null default now(),
  unique (function_id, embedding_type, model)
);
create index function_embeddings_vector_idx on public.function_embeddings using ivfflat (embedding vector_cosine_ops) with (lists = 100);

create table public.tags (
  id uuid primary key default gen_random_uuid(),
  name text not null,
  slug text not null unique,
  created_at timestamptz not null default now()
);

create table public.function_tags (
  function_id uuid not null references public.functions(id) on delete cascade,
  tag_id uuid not null references public.tags(id) on delete cascade,
  primary key (function_id, tag_id)
);

create table public.interactions (
  id uuid primary key default gen_random_uuid(),
  function_id uuid not null references public.functions(id) on delete cascade,
  session_id uuid references public.anonymous_sessions(id) on delete set null,
  user_id uuid references auth.users(id) on delete set null,
  type public.interaction_type not null,
  idempotency_key text not null,
  created_at timestamptz not null default now(),
  unique (function_id, type, idempotency_key)
);
create index interactions_function_type_created_idx on public.interactions (function_id, type, created_at desc);

create table public.submission_events (
  id uuid primary key default gen_random_uuid(),
  function_id uuid references public.functions(id) on delete set null,
  session_id uuid references public.anonymous_sessions(id) on delete set null,
  event text not null,
  outcome text not null,
  metadata jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now()
);
create index submission_events_created_idx on public.submission_events (created_at desc);

create table public.moderation_cases (
  id uuid primary key default gen_random_uuid(),
  function_id uuid not null references public.functions(id) on delete cascade,
  decision public.moderation_status not null,
  evidence jsonb not null default '{}'::jsonb,
  reviewer_id uuid references auth.users(id) on delete set null,
  created_at timestamptz not null default now(),
  resolved_at timestamptz
);

create table public.algorithms (
  id uuid primary key default gen_random_uuid(),
  slug text not null unique,
  title text not null,
  category text not null,
  description text not null,
  content jsonb not null,
  visualization_spec jsonb not null,
  is_published boolean not null default false,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table public.lessons (
  id uuid primary key default gen_random_uuid(),
  slug text not null unique,
  title text not null,
  position integer not null unique,
  summary text not null,
  content jsonb not null,
  is_published boolean not null default false,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create or replace function public.set_updated_at()
returns trigger language plpgsql security invoker set search_path = public as $$
begin
  new.updated_at = now();
  return new;
end;
$$;
create trigger functions_updated_at before update on public.functions for each row execute procedure public.set_updated_at();
create trigger algorithms_updated_at before update on public.algorithms for each row execute procedure public.set_updated_at();
create trigger lessons_updated_at before update on public.lessons for each row execute procedure public.set_updated_at();

alter table public.anonymous_sessions enable row level security;
alter table public.functions enable row level security;
alter table public.function_analyses enable row level security;
alter table public.function_embeddings enable row level security;
alter table public.tags enable row level security;
alter table public.function_tags enable row level security;
alter table public.interactions enable row level security;
alter table public.submission_events enable row level security;
alter table public.moderation_cases enable row level security;
alter table public.algorithms enable row level security;
alter table public.lessons enable row level security;

create policy "published functions are publicly readable" on public.functions for select using (status = 'published' and moderation_status = 'allowed');
create policy "published analysis history is publicly readable" on public.function_analyses for select using (
  exists (select 1 from public.functions f where f.id = function_id and f.status = 'published' and f.moderation_status = 'allowed')
);
create policy "tags are publicly readable" on public.tags for select using (true);
create policy "published function tags are publicly readable" on public.function_tags for select using (
  exists (select 1 from public.functions f where f.id = function_id and f.status = 'published' and f.moderation_status = 'allowed')
);
create policy "published algorithms are publicly readable" on public.algorithms for select using (is_published);
create policy "published lessons are publicly readable" on public.lessons for select using (is_published);

-- API writes use the server-side service role. Do not grant anonymous direct inserts.
