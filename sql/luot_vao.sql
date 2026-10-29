-- Bộ đếm lượt vào ClickAffiliate (29/10/2026): trình duyệt chỉ được GHI, không đọc được (giống clickaffiliate_subscribers).
create table if not exists public.clickaffiliate_views (
  id bigint generated always as identity primary key,
  created_at timestamptz not null default now(),
  path text not null check (char_length(path) <= 200),
  ref text check (char_length(ref) <= 200),
  k text check (char_length(k) <= 60),
  loai text not null default 'xem' check (loai in ('xem','go')),
  khach text check (char_length(khach) <= 40),
  lang text check (char_length(lang) <= 20)
);
alter table public.clickaffiliate_views enable row level security;
revoke all on public.clickaffiliate_views from anon, authenticated;
grant insert (path, ref, k, loai, khach, lang) on public.clickaffiliate_views to anon;
drop policy if exists "anon ghi luot" on public.clickaffiliate_views;
create policy "anon ghi luot" on public.clickaffiliate_views for insert to anon with check (true);
create index if not exists clickaffiliate_views_luc on public.clickaffiliate_views (created_at);
