"""Handle interactions with globus."""

import os
from pprint import pp
import globus_sdk
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
    client.oauth2_start_flow(requested_scopes=get_scopes(gcs_id, id_collection))
    authorize_url = client.oauth2_get_authorize_url()
    print(f"Login URL: {authorize_url}")
    auth_code = input("Code: ").strip()
    token_response = client.oauth2_exchange_code_for_tokens(auth_code)
    pp(token_response.by_resource_server)
    globus_auth_data = token_response.by_resource_server["auth.globus.org"]
    globus_transfer_data = token_response.by_resource_server["transfer.api.globus.org"]
    gcs_transfer_data = token_response.by_resource_server[gcs_id]

    return (
        globus_auth_data["access_token"],
        globus_transfer_data["access_token"],
        gcs_transfer_data["access_token"],
    )


def get_credential(
    domain_name_gcs_manager,
    id_storage_gateway,
    token_gcs_credentials,
    id_connector,
    username,
):
    """Get a user credential, or create one if none exists."""
    print("Querying user credentials")
    resp = requests.get(
        f"https://{domain_name_gcs_manager}/api/user_credentials",
        params={"storage_gateway": id_storage_gateway},
        headers={"Authorization": f"Bearer {token_gcs_credentials}"},
    )
    pp(resp.json())
    for cred in resp.json()["data"]:
        if cred["storage_gateway_id"] == id_storage_gateway:
            print("Got a credential")
            return cred["id"]
    print("No credential... Making a new one.")
    resp = requests.post(
        f"https://{domain_name_gcs_manager}/api/user_credentials",
        headers={"Authorization": f"Bearer {token_gcs_credentials}"},
        json={
            "DATA_TYPE": "user_credential#1.0.0",
            "connector_id": id_connector,
            "username": username,
            "storage_gateway_id": id_storage_gateway,
        },
    )
    pp(resp.json())
    return resp.json()["data"][0]["id"]


def create_collection(
    domain_name_gcs_manager,
    id_storage_gateway,
    id_credential_user,
    token_gcs_collections,
    id_identity,
    collection_base_path,
    id_collection_mapped,
):
    # pylint: disable=too-many-arguments
    """Create a collection using pre-configured authentication."""
    print("Making a new collection")
    resp = requests.post(
        f"https://{domain_name_gcs_manager}/api/collections",
        headers={"Authorization": f"Bearer {token_gcs_collections}"},
        json={
            "DATA_TYPE": "collection#1.4.0",
            "collection_type": "guest",
            "display_name": "Test Guest Collection 2",
            "identity_id": id_identity,
            "storage_gateway_id": id_storage_gateway,
            "collection_base_path": collection_base_path,
            "public": True,
            "user_credential_id": id_credential_user,
            "mapped_collection_id": id_collection_mapped,
        },
    )
    pp(resp.json())


def main_native():
    """Create a collection interactively."""
    _, _, token_gcs = get_tokens_native(
        CLIENT_ID_NATIVE, ENDPOINT_ID_GRAHAM, COLLECTION_ID_GRAHAM
    )
    id_credential_user = get_credential(
        GCS_MANAGER_DOMAIN_NAME,
        STORAGE_GATEWAY_ID_GRAHAM,
        token_gcs,
        ID_CONNECTOR,
        USERNAME,
    )
    create_collection(
        GCS_MANAGER_DOMAIN_NAME,
        STORAGE_GATEWAY_ID_GRAHAM,
        id_credential_user,
        token_gcs,
        USER_ID,
        "/home/tkuehn/code",
        COLLECTION_ID_GRAHAM,
    )


def main_nonnative():
    """Create a collection non-interactively.

    This doesn't seem to work at this point.
    """
    authorizer_credentials = globus_sdk.ClientCredentialsAuthorizer(
        globus_sdk.ConfidentialAppAuthClient(CLIENT_ID_NONNATIVE, CLIENT_SECRET),
        get_scope_credentials(ENDPOINT_ID_GRAHAM),
    )
    authorizer_collections = globus_sdk.ClientCredentialsAuthorizer(
        globus_sdk.ConfidentialAppAuthClient(CLIENT_ID_NONNATIVE, CLIENT_SECRET),
        get_scope_collections(ENDPOINT_ID_GRAHAM, COLLECTION_ID_GRAHAM),
    )
    id_credential_user = get_credential(
        GCS_MANAGER_DOMAIN_NAME,
        STORAGE_GATEWAY_ID_GRAHAM,
        authorizer_credentials.access_token,
        ID_CONNECTOR,
        USERNAME,
    )
    create_collection(
        GCS_MANAGER_DOMAIN_NAME,
        STORAGE_GATEWAY_ID_GRAHAM,
        id_credential_user,
        authorizer_collections.access_token,
        USER_ID,
        "/home/tkuehn/code",
        COLLECTION_ID_GRAHAM,
    )


if __name__ == "__main__":
    main_native()
