create extension if not exists pgcrypto;

create table if not exists public.salary_predictions (
    id uuid primary key default gen_random_uuid(),
    created_at timestamptz not null default now(),
    experience_level text not null check (experience_level in ('EN', 'MI', 'SE', 'EX')),
    employment_type text not null check (employment_type in ('FT', 'PT', 'CT', 'FL')),
    job_title text not null,
    employee_residence text not null check (char_length(employee_residence) = 2),
    company_location text not null check (char_length(company_location) = 2),
    company_size text not null check (company_size in ('S', 'M', 'L')),
    remote_ratio integer not null check (remote_ratio in (0, 50, 100)),
    predicted_salary_usd numeric(12, 2) not null,
    peer_group_label text not null,
    peer_group_size integer not null,
    peer_median_salary_usd numeric(12, 2) not null,
    peer_min_salary_usd numeric(12, 2) not null,
    peer_max_salary_usd numeric(12, 2) not null,
    comparison_text text not null,
    explanation_summary text not null
);

create index if not exists idx_salary_predictions_created_at
    on public.salary_predictions (created_at desc);

create index if not exists idx_salary_predictions_job_title
    on public.salary_predictions (job_title);

alter table public.salary_predictions enable row level security;

drop policy if exists "salary_predictions_public_read" on public.salary_predictions;
create policy "salary_predictions_public_read"
    on public.salary_predictions
    for select
    using (true);

drop policy if exists "salary_predictions_service_role_insert" on public.salary_predictions;
create policy "salary_predictions_service_role_insert"
    on public.salary_predictions
    for insert
    to service_role
    with check (true);
