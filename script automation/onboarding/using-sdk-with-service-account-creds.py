"""
Example: Authenticate with Service Account Credentials

PURPOSE: Demo authentication using client ID + secret (no browser required)
USAGE: python using-sdk-with-service-account-creds.py
WHEN: Testing service account, creating automation scripts, CI/CD templates

DEMONSTRATES:
  - ArthurClientCredentialsAPISession authentication
  - Listing workspaces and projects
  - Service account API usage

REQUIRES:
  - Client ID (from service-account-creation.py)
  - Client Secret (from service-account-creation.py)

CONFIGURE: Update CLIENT_ID and CLIENT_SECRET

USE IN PRODUCTION: Load from environment variables, not hardcoded
"""

from arthur_client.api_bindings import WorkspacesV1Api, ProjectsV1Api
from arthur_client.api_bindings.api_client import ApiClient
from arthur_client.auth import (
    ArthurOAuthSessionAPIConfiguration,
    ArthurClientCredentialsAPISession,
    ArthurOIDCMetadata,
)

CLIENT_ID = "<FILL IN Service account CLIENT ID>"
CLIENT_SECRET = "<FILL IN Service account CLIENT SECRET>"
ARTHUR_HOST = "https://platform.arthur.ai"

if __name__ == "__main__":
    # authorize the SDK using credentials from a service account (client ID + client secret)
    # instead of with user credentials via the browser
    # service accounts should only be used for automated systems to integrate with Arthur
    # for normal users, it's better to use browser based authentication
    sess = ArthurClientCredentialsAPISession(
        client_id=CLIENT_ID,
        client_secret=CLIENT_SECRET,
        metadata=ArthurOIDCMetadata(arthur_host=ARTHUR_HOST),
    )
    api_client = ApiClient(
        configuration=ArthurOAuthSessionAPIConfiguration(session=sess)
    )

    workspaces_client = WorkspacesV1Api(api_client=api_client)
    projects_client = ProjectsV1Api(api_client=api_client)

    # simple example, list the projects in a workspace using the service account credentials
    workspaces_resp = workspaces_client.get_workspaces()
    projects_resp = projects_client.get_projects(
        workspace_id=workspaces_resp.records[0].id
    )

    print(f"Found projects: {[p.name for p in projects_resp.records]}")
