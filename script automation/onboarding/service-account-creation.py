"""
Create Arthur Service Account for Automation

PURPOSE: Create service account with client credentials for machine-to-machine auth
USAGE: python service-account-creation.py
WHEN: Setting up CI/CD, automated jobs, system integrations

CREATES:
  - Service account user
  - Client ID and Client Secret (SAVE THESE - shown only once!)
  - Assigns Organization Super Admin role
  - Adds to specified group

REQUIRES:
  - Browser authentication (first time)
  - Organization Admin permissions

CONFIGURE: Update GROUP_NAME to your actual group

SECURITY: Store credentials in secure vault (AWS Secrets Manager, etc.)

NEXT STEP: Test with using-sdk-with-service-account-creds.py
"""

from arthur_client.api_bindings import UsersV1Api, AuthorizationV1Api, GroupsV1Api
from arthur_client.api_bindings.models import *
from arthur_client.api_bindings.api_client import ApiClient
from arthur_client.auth import ArthurOAuthSessionAPIConfiguration, DeviceAuthorizer

ARTHUR_HOST = "https://platform.arthur.ai"

if __name__ == "__main__":
    # authorize the SDK using the browser
    sess = DeviceAuthorizer(arthur_host=ARTHUR_HOST).authorize()
    api_client = ApiClient(
        configuration=ArthurOAuthSessionAPIConfiguration(session=sess)
    )

    users_client = UsersV1Api(api_client=api_client)
    authz_client = AuthorizationV1Api(api_client=api_client)
    groups_client = GroupsV1Api(api_client=api_client)

    # TODO adjust permissions as necessary, for now we're giving the service account
    #  Organization Super Admin role and adding them to a group
    #  which is likely duplicative since both the group and the role have the same
    #  permissions. This code is meant to be an example only.

    # find role ID by name for service account to use
    ROLE_NAME = "Organization Super Admin"
    roles_resp = authz_client.list_roles(
        name=ROLE_NAME, organization_bindable=True, page_size=1
    )
    role = roles_resp.records[0]

    # find group ID by name for service account to use
    # TODO: Update this to your actual group name
    GROUP_NAME = "INSERT_GROUP_NAME_HERE"
    groups = groups_client.get_groups(name=GROUP_NAME, page_size=1)
    group = groups.records[0]

    # create a service account that has machine-to-machine credentials for automations
    # to use with the Arthur API
    service_account_user = users_client.post_organization_service_account(
        post_service_account=PostServiceAccount(
            name="Service Account",
        )
    )

    print(f"Created service account with ID: {service_account_user.id}")
    print(f"Service account credentials (note these will not be shown again)")
    print(f"Client ID: {service_account_user.credentials.client_id}")
    print(
        f"Client Secret: {service_account_user.credentials.client_secret.get_secret_value()}"
    )
    print("")

    # assign service account the role from above
    authz_client.post_org_role_binding(
        post_role_binding=PostRoleBinding(
            role_id=role.id,
            user_id=service_account_user.id,
        )
    )

    print(f"Assigned service account user role {ROLE_NAME} - {role.id}")

    # add service account to group from above
    groups_client.assign_users_to_group(
        group_id=group.id,
        post_group_membership=PostGroupMembership(user_ids=[service_account_user.id]),
    )

    print(f"Added service account user to group {GROUP_NAME} - {group.id}")
