from __future__ import annotations

import argparse
import sys

import requests

from config import get_settings


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Call the PayScope prediction API.")
    parser.add_argument("--experience-level", default="SE")
    parser.add_argument("--employment-type", default="FT")
    parser.add_argument("--job-title", default="Data Scientist")
    parser.add_argument("--employee-residence", default="US")
    parser.add_argument("--company-location", default="US")
    parser.add_argument("--company-size", default="M")
    parser.add_argument("--remote-ratio", type=int, default=100)
    return parser


def main() -> int:
    args = build_parser().parse_args()
    settings = get_settings()
    params = {
        "experience_level": args.experience_level,
        "employment_type": args.employment_type,
        "job_title": args.job_title,
        "employee_residence": args.employee_residence,
        "company_location": args.company_location,
        "company_size": args.company_size,
        "remote_ratio": args.remote_ratio,
    }

    try:
        response = requests.get(
            f"{settings.fastapi_base_url.rstrip('/')}/predict",
            params=params,
            timeout=settings.request_timeout_seconds,
        )
        response.raise_for_status()
        payload = response.json()
    except requests.exceptions.Timeout:
        print("Request timed out. Confirm the FastAPI server is running and try again.", file=sys.stderr)
        return 1
    except requests.exceptions.ConnectionError:
        print("Could not connect to the API. Start FastAPI before running this client.", file=sys.stderr)
        return 1
    except requests.exceptions.HTTPError as exc:
        detail = exc.response.text if exc.response is not None else str(exc)
        print(f"API returned an error: {detail}", file=sys.stderr)
        return 1
    except ValueError:
        print("The API response was not valid JSON.", file=sys.stderr)
        return 1

    predicted_salary = payload["predicted_salary_usd"]
    peer_context = payload["peer_context"]

    print("Prediction successful.")
    print(f"Predicted salary (USD): ${predicted_salary:,.0f}")
    print(f"Peer group: {peer_context['match_label']}")
    print(f"Sample size: {peer_context['sample_size']}")
    print(peer_context["comparison_text"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

