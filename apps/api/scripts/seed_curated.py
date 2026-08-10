from __future__ import annotations

from supabase import create_client

from app.seeding import seed_curated_functions
from app.settings import get_settings


def main() -> None:
    settings = get_settings()
    if not settings.supabase_url or not settings.supabase_service_role_key:
        raise SystemExit("Set SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY before seeding curated content.")
    count = seed_curated_functions(create_client(settings.supabase_url, settings.supabase_service_role_key))
    print(f"Seeded or updated {count} curated functions.")


if __name__ == "__main__":
    main()
