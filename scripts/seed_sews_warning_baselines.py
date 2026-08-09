from pprint import pprint

from app.routes.sews_evidence import get_sews_supabase_client
from app.services.sews_warning_baseline_service import (
    SEWSWarningBaselineService,
)


def main():
    db = get_sews_supabase_client()
    service = SEWSWarningBaselineService(db)

    result = service.seed_all()
    pprint(result)


if __name__ == "__main__":
    main()
