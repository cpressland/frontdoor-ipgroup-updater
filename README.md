# Azure Front Door IP Group Updater

Simple application that updates IP Groups in Microsoft Azure with the IP Ranges currently configured for Azure Front Door. While Network Security Groups have the required service tags to limit acccess to Azure Front Door, Azure Firewall does not. This aims to mitigate that.

# Usage

## Create a Service Principal

The Application requires a Service Principal with Contributor access to the IP Group you intend to use. The below assumes you've already created the relevant resource.

Firstly, create a Service Principal with the following:

```
$ az ad sp create-for-rbac -n "Azure Front Door IP Group Updater"
```

This should return a payload similar to the below, make a note of it for later:

```json
{
  "appId": "8fcd040b-6966-452e-b006-83670131e941",
  "displayName": "Azure Front Door IP Group Updater",
  "password": "some_super_secret_secret",
  "tenant": "e457378e-e0b3-4edc-95a8-20de1ea662f1"
}
```

**Note:** _by default the secret created for this user will expire in 12 months, make sure to setup a way to detect this and handle it appropriately._

## Assign the Application to the IP Group

Get the Principal ID of the new Service Principal you just created:

```shell
$ az ad sp show --id "{appId}" | jq -r .id
```

Now use that to assign the Service Principal to the AzureRM Resource.

```shell
$ az role assignment create \
  --assignee "{princial_ip}" \
  --role "Contributor" \
  --scope "/subscriptions/{your_subscription}/resourceGroups/{your_resource_group}/providers/Microsoft.Network/ipGroups/{ip_group_name}" 
```

## Create and Assign a Custom Role for viewing Service Tags

Create a file called `role.json` with the following content

```json
{
    "Name": "Service Tag Reader",
    "IsCustom": true,
    "Description": "Reads Service Tags via Rest API",
    "Actions": [
        "Microsoft.Network/locations/serviceTagDetails/read"
    ],
    "NotActions": [],
    "AssignableScopes": [
        "/subscriptions/{your_subscription}",
    ]
}
```

Now apply this with:

```shell
$ az role definition create --role-definition role.json
```

Finally, assign the role with:

```shell
$ az role assignment create \
  --assignee "{princial_ip}" \
  --role "Service Tag Reader" \
  --scope "/subscriptions/{your_subscription}"
```

## Run the Application

The Application can be run in one of four ways:

1) Locally in Python 3.10, use a `.env` or `config.toml` file, or manually do a bunch of `export` commands if you're into that.
2) Locally via Docker
3) Azure Kubernetes Service using Environment Variables
4) Azure Kubernetes Service using `config.toml`

Below is an example of running this with Environment Variables using Docker:

```shell
$ docker run --rm --name frontdoor-iprange-updater \
    -e application_id="8fcd040b-6966-452e-b006-83670131e941" \
    -e application_secret="some_super_secret_secret" \
    -e tenant_id="e457378e-e0b3-4edc-95a8-20de1ea662f1" \
    -e subscription_id="3fbfae19-cdb6-49b7-b2cb-b297d067fa92" \
    -e resource_group_name="uksouth-firewall" \
    -e ip_group_name="frontdoor_ips" \
    ghcr.io/cpressland/frontdoor-ipgroup-updater:latest
```

For an AKS install, I'd recommend you use Flux v2 and use a `configMapGenerator` to inject a `config.toml` file into `/app`, and inject the `application_secret` into a file called `/var/run/secrets/frontdoor-ipgroup-updater/application_secret`, using a `secretGenerator` or whatever mechanism you prefer. `config.toml` example:

```
application_id = "8fcd040b-6966-452e-b006-83670131e941"
tenant_id = "e457378e-e0b3-4edc-95a8-20de1ea662f1"
subscription_id = "3fbfae19-cdb6-49b7-b2cb-b297d067fa92"
resource_group_name = "uksouth-firewall"
ip_group_name = "frontdoor_ips"
```

Note, `application_secret` is missing from the config file as its expected that you'd inject it via the aformentioned file in `/var/run/secrets`. Pydantic allows any configuration to be stored as a file, config, or environment variable. So you can mix and match for whatever works for you.
