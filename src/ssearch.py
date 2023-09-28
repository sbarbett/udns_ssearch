import requests
import csv
import argparse
import urllib.parse
import json
import os
from tqdm import tqdm

BASE_URL = "https://api.ultradns.com"

def get_primary_token(username=None, password=None, token=None):
    if token:
        print("Warning: A masquerade token cannot be refreshed upon expiry.")
        return token, None
    auth_endpoint = f"{BASE_URL}/authorization/token"
    auth_data = {
        "grant_type": "password",
        "username": username,
        "password": password
    }
    response = requests.post(auth_endpoint, data=auth_data, headers={"Content-Type": "application/x-www-form-urlencoded"})
    response.raise_for_status()
    return response.json().get("accessToken"), response.json().get("refreshToken")

def refresh_token(refresh_token):
    auth_endpoint = f"{BASE_URL}/authorization/token"
    auth_data = {
        "grant_type": "refresh_token",
        "refresh_token": refresh_token
    }
    response = requests.post(auth_endpoint, data=auth_data, headers={"Content-Type": "application/x-www-form-urlencoded"})
    response.raise_for_status()
    return response.json().get("accessToken")

def make_request(method, url, token, refresh_token, **kwargs):
    headers = {"Authorization": f"Bearer {token}"}
    response = requests.request(method, url, headers=headers, **kwargs)
    if response.status_code == 403:
        return response  # Return the response to handle the error at the caller level
    if response.status_code == 401 and refresh_token:
        new_token = refresh_token(refresh_token)
        headers["Authorization"] = f"Bearer {new_token}"
        response = requests.request(method, url, headers=headers, **kwargs)
    response.raise_for_status()
    return response

def get_subaccounts(token, refresh_token, offset=0):
    subaccounts = []
    while True:
        response = make_request("get", f"{BASE_URL}/subaccounts?limit=1000&offset={offset}", token, refresh_token)
        if response.status_code == 403 and 'do not have permissions' in response.text:
            print("Error: You do not have permissions to access sub-accounts. Ensure you're using a reseller account.")
            exit(1)
        response.raise_for_status()
        data = response.json()
        subaccounts.extend(data.get("accounts", []))
        if data["resultInfo"]["returnedCount"] < 1000:
            break
        offset += 1000
    return subaccounts

def get_subaccount_token(account_name, primary_token):
    headers = {
        "Authorization": f"Bearer {primary_token}",
        "Content-Type": "application/json"
    }
    try:
        response = requests.post(f"{BASE_URL}/subaccounts/{account_name.replace(' ', '%20')}/token", headers=headers)
        response.raise_for_status()
        return response.json()["accessToken"]
    except requests.HTTPError as e:
        if 'is suspended' in response.text:
            print(f"Skipping suspended sub-account: {account_name}")
            return None
        else:
            raise

def get_zones(token, cursor=""):
    headers = {"Authorization": f"Bearer {token}"}
    zones = []
    while True:
        response = requests.get(f"{BASE_URL}/v2/zones?limit=1000&cursor={cursor}", headers=headers)
        response.raise_for_status()
        data = response.json()
        zones.extend(data.get("zones", []))
        cursor = data["cursorInfo"].get("next")
        if not cursor:
            break
    return zones

def get_pools(zone_name, token, offset=0):
    headers = {"Authorization": f"Bearer {token}"}
    pools = []
    while True:
        response = requests.get(f"{BASE_URL}/v2/zones/{urllib.parse.quote(zone_name)}/rrsets?q=kind:POOLS&limit=1000&offset={offset}", headers=headers)
        if response.status_code == 404:
            break
        response.raise_for_status()
        data = response.json()
        pools.extend(data.get("rrSets", []))
        if data["resultInfo"]["returnedCount"] < 1000:
            break
        offset += 1000
    return pools

def main(username=None, password=None, token=None, output_file=None, format="json"):
    primary_token, refresh_token_val = get_primary_token(username, password, token)
    subaccounts = get_subaccounts(primary_token, refresh_token_val)
    data = [{"Sub Account Name": "", "Zone Name": "", "Pool Name": "", "Pool Type": ""}]
    
    for account in tqdm(subaccounts, desc="Processing sub-accounts"):
        account_name = account.get("accountName")
        subaccount_token = get_subaccount_token(account_name, primary_token)
        if not subaccount_token:
            continue
        zones = get_zones(subaccount_token)
        for zone in tqdm(zones, desc="Processing zones for " + account_name, leave=False):
            zone_name = zone["properties"]["name"]
            pools = get_pools(zone_name, subaccount_token)
            for pool in pools:
                pool_name = pool["ownerName"]
                pool_type = pool["profile"]["@context"]
                data.append({"Sub Account Name": account_name, "Zone Name": zone_name, "Pool Name": pool_name, "Pool Type": pool_type})

    if output_file:
        with open(os.path.expanduser(output_file), 'w') as outfile:
            if format == "json":
                json.dump(data, outfile, indent=4)
            elif format == "csv":
                csvwriter = csv.DictWriter(outfile, fieldnames=data[0].keys())
                csvwriter.writeheader()
                for row in data[1:]:
                    csvwriter.writerow(row)
    else:
        if format == "json":
            print(json.dumps(data, indent=4))
        elif format == "csv":
            csvwriter = csv.DictWriter(sys.stdout, fieldnames=data[0].keys())
            csvwriter.writeheader()
            for row in data[1:]:
                csvwriter.writerow(row)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="UltraDNS Subaccounts Zones and Pools Finder")
    
    parser.add_argument("--token", help="Directly pass the Bearer token")
    
    auth_group = parser.add_argument_group('authentication', 'Username and Password for authentication')
    auth_group.add_argument("--username", help="Username for authentication")
    auth_group.add_argument("--password", help="Password for authentication")
    
    parser.add_argument("--output-file", help="Output file name. If not provided, prints to terminal.")
    parser.add_argument("--format", choices=["json", "csv"], default="json", help="Output format: 'json' or 'csv'. Default is 'json'.")
    
    args = parser.parse_args()
    
    if args.token is None and (args.username is None or args.password is None):
        parser.error("When token is not provided, both username and password are required")
    
    main(username=args.username, password=args.password, token=args.token, output_file=args.output_file, format=args.format)
