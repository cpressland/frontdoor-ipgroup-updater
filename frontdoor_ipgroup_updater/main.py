import argparse
from ipaddress import IPv4Network, IPv6Network, ip_network
from sys import exit

import requests
from msal import ConfidentialClientApplication

from frontdoor_ipgroup_updater.logging import log
from frontdoor_ipgroup_updater.settings import settings


def _get_auth_token() -> str:
    app = ConfidentialClientApplication(
        client_id=str(settings.application_id),
        client_credential=settings.application_secret,
        authority=f"https://login.microsoftonline.com/{settings.tenant_id}",
    )
    token = app.acquire_token_for_client(scopes=["https://management.core.windows.net//.default"])
    if "access_token" in token:
        return token["access_token"]
    else:
        log.warning(
            "Failed to get auth token", extra={"error": token["error"], "error_description": token["error_description"]}
        )
        exit(1)


def _filter_ip_versions(networks: list) -> dict:
    ipv4 = []
    ipv6 = []
    for network in networks:
        if type(ip_network(network)) == IPv4Network:
            ipv4.append(network)
        elif type(ip_network(network)) == IPv6Network:
            ipv6.append(network)
        else:
            log.warning("Unknown Network Detected", extra={"network": network})
    log.warning("Successfully Split IPv4 and IPv6 Addresses", extra={"ipv4": ipv4, "ipv6": ipv6})
    return {"ipv4": ipv4, "ipv6": ipv6}


def _get_service_tag_details(auth_token):
    url = (
        "https://management.azure.com"
        f"/subscriptions/{settings.subscription_id}"
        "/providers/Microsoft.Network/locations/uksouth/serviceTagDetails"
    )
    data = requests.get(
        url,
        headers={"Authorization": f"Bearer {auth_token}", "Content-Type": "application/json"},
        params={"api-version": "2022-01-01", "tagName": "AzureFrontDoor.Backend"},
    ).json()
    return data["value"][0]["properties"]["addressPrefixes"]


def update_azure_ip_group(auth_token: str, addresses: list, dry_run: bool) -> None:
    subscription_id = settings.subscription_id
    resource_group_name = settings.resource_group_name
    ip_group_name = settings.ip_group_name
    resource_url = (
        "https://management.azure.com"
        f"/subscriptions/{subscription_id}"
        f"/resourceGroups/{resource_group_name}"
        f"/providers/Microsoft.Network/ipGroups/{ip_group_name}"
        "?api-version=2022-01-01"
    )

    existing_metadata = requests.get(
        resource_url, headers={"Authorization": f"Bearer {auth_token}", "Content-Type": "application/json"}
    ).json()

    metadata_tags = existing_metadata.get("tags", {})
    metadata_location = existing_metadata.get("location")
    metadata_addresses = existing_metadata.get("properties", {}).get("ipAddresses", [])

    log.warning(
        "Successfully pulled existing resource metadata",
        extra={
            "addresses": metadata_addresses,
            "tags": metadata_tags,
            "location": metadata_location,
        },
    )

    if dry_run:
        log.warning("Dry Run mode enabled, skipping update")
    elif metadata_addresses == addresses:
        log.warning("No IP Addresses to change, skipping update")
    else:
        log.warning("Submitting new list of IPs to Azure API", extra={"ips": addresses})
        try:
            update_group = requests.put(
                resource_url,
                headers={"Authorization": f"Bearer {auth_token}", "Content-Type": "application/json"},
                json={
                    "tags": metadata_tags,
                    "location": metadata_location,
                    "properties": {"ipAddresses": addresses},
                },
            )
            update_group.raise_for_status()
            log.warning("Successfully updated IP Group with latest set of networks")
        except Exception as e:
            log.warning("Something went wrong", exc_info=e)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    dry_run = False
    if args.dry_run:
        dry_run = True
    auth_token = _get_auth_token()
    frontdoor_ips = _get_service_tag_details(auth_token=auth_token)
    frontdoor_ip_versions = _filter_ip_versions(frontdoor_ips)
    if len(frontdoor_ip_versions["ipv4"]) > settings.minimum_acceptable_v4_networks:
        update_azure_ip_group(auth_token=auth_token, addresses=frontdoor_ip_versions["ipv4"], dry_run=dry_run)
    else:
        log.warning(f"Less than {settings.minimum_acceptable_v4_networks} IPv4 Networks detected, cowardly exiting")
        exit(1)
