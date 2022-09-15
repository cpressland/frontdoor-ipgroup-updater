import json
from typing import Set

import bs4
import requests


def get_azure_ip_ranges() -> Set[str]:
    page = "https://www.microsoft.com/en-us/download/confirmation.aspx?id=56519"
    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 11_0_1) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/87.0.4280.66 Safari/537.36"
    }

    resp = requests.get(page, headers=headers)
    assert resp.status_code == 200

    soup = bs4.BeautifulSoup(resp.content, features="html.parser")
    json_file = soup.find("a", attrs={"data-bi-id": "downloadretry"}).attrs["href"]

    file_resp = requests.get(json_file, headers=headers)
    data = json.loads(file_resp.content)
    frontdoor = next((section for section in data["values"] if section["id"] == "AzureFrontDoor.Frontend"))
    return set(frontdoor["properties"]["addressPrefixes"])


if __name__ == "__main__":
    ips = get_azure_ip_ranges()
    for ip in ips:
        print(ip)
