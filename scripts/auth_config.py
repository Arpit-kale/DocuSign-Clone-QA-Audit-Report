import os


def get_http_credentials() -> tuple[str, str]:
    username = os.environ.get("DOCUSIGN_QA_USERNAME")
    password = os.environ.get("DOCUSIGN_QA_PASSWORD")
    if not username or not password:
        raise RuntimeError(
            "Set DOCUSIGN_QA_USERNAME and DOCUSIGN_QA_PASSWORD before running this script."
        )
    return username, password
