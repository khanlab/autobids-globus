"""Handle interactions with globus."""

import os
from pprint import pp
import random
import string
import globus_sdk
from globus_sdk.tokenstorage import SimpleJSONFileAdapter
import requests

CLIENT_ID_NATIVE = os.environ.get("CLIENT_ID_NATIVE")
CLIENT_ID_NONNATIVE = os.environ.get("CLIENT_ID_NONNATIVE")
CLIENT_SECRET = os.environ["CLIENT_SECRET"]
ENDPOINT_ID_GRAHAM = os.environ["ENDPOINT_ID_GRAHAM"]
USER_ID = os.environ["USER_ID"]
COLLECTION_ID_GRAHAM = os.environ["COLLECTION_ID_GRAHAM"]
STORAGE_GATEWAY_ID_GRAHAM = os.environ["STORAGE_GATEWAY_ID_GRAHAM"]
GCS_MANAGER_DOMAIN_NAME = os.environ["GCS_MANAGER_DOMAIN_NAME"]
ID_CONNECTOR = os.environ["ID_CONNECTOR"]
USERNAME = os.environ["USERNAME"]
TOKEN_FILE = os.environ["TOKEN_FILE"]

FILE_ADAPTER = SimpleJSONFileAdapter(TOKEN_FILE)


def get_scope_credentials(id_endpoint):
    """Construct the scope needed to interact with the credentials API."""
    return f"urn:globus:auth:scope:{id_endpoint}:manage_collections"


def get_scope_collections(id_endpoint, id_collection):
    """Construct the scope needed to interact with the collections API."""
    return (
        f"urn:globus:auth:scope:{id_endpoint}:manage_collections"
        f"[*https://auth.globus.org/scopes/{id_collection}/data_access]"
    )


def get_scopes(id_endpoint, id_collection):
    """Get the scopes needed to create a collection as a native app."""
    return [
        globus_sdk.scopes.AuthScopes.openid,
        globus_sdk.scopes.AuthScopes.profile,
        globus_sdk.scopes.AuthScopes.email,
        globus_sdk.scopes.AuthScopes.view_identity_set,
        globus_sdk.scopes.TransferScopes.all,
        get_scope_collections(id_endpoint, id_collection),
    ]


def get_tokens_native(client_id, gcs_id, id_collection):
    """Get the tokens needed to create a collection as a native app."""

    client = globus_sdk.NativeAppAuthClient(client_id)
    if not FILE_ADAPTER.file_exists():
        client.oauth2_start_flow(
            refresh_tokens=True, requested_scopes=get_scopes(gcs_id, id_collection)
        )
        authorize_url = client.oauth2_get_authorize_url()
        print(f"Login URL: {authorize_url}")
        auth_code = input("Code: ").strip()
        token_response = client.oauth2_exchange_code_for_tokens(auth_code)
        pp(token_response.by_resource_server)
        FILE_ADAPTER.store(token_response)
        globus_auth_data = token_response.by_resource_server["auth.globus.org"]
        globus_transfer_data = token_response.by_resource_server[
            "transfer.api.globus.org"
        ]
        gcs_transfer_data = token_response.by_resource_server[gcs_id]
    else:
        globus_auth_data = FILE_ADAPTER.get_token_data("auth.globus.org")
        globus_transfer_data = FILE_ADAPTER.get_token_data("transfer.api.globus.org")
        gcs_transfer_data = FILE_ADAPTER.get_token_data(gcs_id)

    return (
        client,
        globus_auth_data,
        globus_transfer_data,
        gcs_transfer_data,
    )


def get_credential(
    domain_name_gcs_manager,
    id_storage_gateway,
    authorizer_gcs_credentials,
    id_connector,
    username,
):
    """Get a user credential, or create one if none exists."""
    print("Querying user credentials")
    resp = requests.get(
        f"https://{domain_name_gcs_manager}/api/user_credentials",
        params={"storage_gateway": id_storage_gateway},
        headers={
            "Authorization": authorizer_gcs_credentials.get_authorization_header()
        },
    )
    pp(resp.json())
    for cred in resp.json()["data"]:
        if cred["storage_gateway_id"] == id_storage_gateway:
            print("Got a credential")
            return cred["id"]
    print("No credential... Making a new one.")
    resp = requests.post(
        f"https://{domain_name_gcs_manager}/api/user_credentials",
        headers={
            "Authorization": authorizer_gcs_credentials.get_authorization_header()
        },
        json={
            "DATA_TYPE": "user_credential#1.0.0",
            "connector_id": id_connector,
            "username": username,
            "storage_gateway_id": id_storage_gateway,
        },
    )
    pp(resp.json())
    return resp.json()["data"][0]["id"]


def add_read_permission(transfer_client, auth_client, id_collection_guest, email):
    """Add read permission for a given compute canada user."""
    id_identity = auth_client.get_identities(
        usernames=f"{email}@computecanada.ca"
    ).data["identities"][0]["id"]
    result = transfer_client.add_endpoint_acl_rule(
        id_collection_guest,
        {
            "DATA_TYPE": "access",
            "principal_type": "identity",
            "principal": id_identity,
            "path": "/",
            "permissions": "r",
        },
    )
    print(result["access_id"])


def create_collection(
    domain_name_gcs_manager,
    id_storage_gateway,
    id_credential_user,
    authorizer_gcs_collections,
    display_name,
    id_identity,
    collection_base_path,
    id_collection_mapped,
):
    # pylint: disable=too-many-arguments
    """Create a collection using pre-configured authentication."""
    print("Making a new collection")
    resp = requests.post(
        f"https://{domain_name_gcs_manager}/api/collections",
        headers={
            "Authorization": authorizer_gcs_collections.get_authorization_header()
        },
        json={
            "DATA_TYPE": "collection#1.4.0",
            "collection_type": "guest",
            "display_name": display_name,
            "identity_id": id_identity,
            "storage_gateway_id": id_storage_gateway,
            "collection_base_path": collection_base_path,
            "public": False,
            "user_credential_id": id_credential_user,
            "mapped_collection_id": id_collection_mapped,
        },
    )
    pp(resp.json())
    return resp.json()["data"][0]["id"]


def main_native():
    """Create a collection interactively."""
    client, tokens_auth, tokens_transfer, tokens_gcs = get_tokens_native(
        CLIENT_ID_NATIVE, ENDPOINT_ID_GRAHAM, COLLECTION_ID_GRAHAM
    )
    authorizer_auth = globus_sdk.RefreshTokenAuthorizer(
        tokens_auth["refresh_token"],
        client,
        access_token=tokens_auth["access_token"],
        expires_at=tokens_auth["expires_at_seconds"],
        on_refresh=FILE_ADAPTER.on_refresh,
    )
    authorizer_transfer = globus_sdk.RefreshTokenAuthorizer(
        tokens_transfer["refresh_token"],
        client,
        access_token=tokens_transfer["access_token"],
        expires_at=tokens_transfer["expires_at_seconds"],
        on_refresh=FILE_ADAPTER.on_refresh,
    )
    authorizer_gcs = globus_sdk.RefreshTokenAuthorizer(
        tokens_gcs["refresh_token"],
        client,
        access_token=tokens_gcs["access_token"],
        expires_at=tokens_gcs["expires_at_seconds"],
        on_refresh=FILE_ADAPTER.on_refresh,
    )
    id_credential_user = get_credential(
        GCS_MANAGER_DOMAIN_NAME,
        STORAGE_GATEWAY_ID_GRAHAM,
        authorizer_gcs,
        ID_CONNECTOR,
        USERNAME,
    )
    id_collection_guest = create_collection(
        GCS_MANAGER_DOMAIN_NAME,
        STORAGE_GATEWAY_ID_GRAHAM,
        id_credential_user,
        authorizer_gcs,
        f"sdk_collection_{''.join(random.choices(string.ascii_lowercase, k=6))}",
        USER_ID,
        "/home/tkuehn/code",
        COLLECTION_ID_GRAHAM,
    )
    add_read_permission(
        globus_sdk.TransferClient(
            authorizer=authorizer_transfer,
        ),
        globus_sdk.AuthClient(authorizer=authorizer_auth),
        id_collection_guest,
        "switt4",
    )


if __name__ == "__main__":
    main_native()
