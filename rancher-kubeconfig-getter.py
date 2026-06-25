import requests
import yaml
import getpass
import argparse
import os
import sys

combined_kubeconfig = {
    'apiVersion': 'v1',
    'kind': 'Config',
    'clusters': [],
    'users': [],
    'contexts': [],
    'current-context': None,
}


def get_rancher_token(rancher_url, username, password):
    login_url = f'{rancher_url}/v1-public/login'
    payload = {
        'type': 'activeDirectoryProvider',
        'username': username,
        'password': password,
        'description': 'rancher-kubeconfig-getter',
        'responseType': 'cookie',
        'ttl': 3600,
    }
    response = requests.post(login_url, json=payload)
    if response.status_code != 200:
        print(f"  Login failed: {response.status_code} - {response.text}")
        return None
    token = response.cookies.get('R_SESS')
    if not token:
        print(f"  Login succeeded but no R_SESS cookie received")
        return None
    return token


def fetch_kubeconfigs_from_rancher(rancher_url, api_token):
    headers = {
        'Authorization': f'Bearer {api_token}'
    }

    response = requests.get(f'{rancher_url}/v3/clusters', headers=headers)

    if response.status_code != 200:
        print(f"  Failed to list clusters: {response.status_code} - {response.text}")
        return [], []

    clusters = response.json().get('data', [])
    succeeded = []
    failed = []

    for cluster in clusters:
        cluster_id = cluster['id']
        cluster_name = cluster['name']

        kubeconfig_response = requests.post(
            f'{rancher_url}/v3/clusters/{cluster_id}?action=generateKubeconfig',
            headers=headers,
        )

        if kubeconfig_response.status_code == 200:
            kubeconfig = kubeconfig_response.json().get('config')
            if kubeconfig:
                kubeconfig_data = yaml.safe_load(kubeconfig)

                combined_kubeconfig['clusters'].extend(kubeconfig_data['clusters'])
                combined_kubeconfig['users'].extend(kubeconfig_data['users'])
                combined_kubeconfig['contexts'].extend(kubeconfig_data['contexts'])

                if combined_kubeconfig['current-context'] is None and kubeconfig_data.get('current-context'):
                    combined_kubeconfig['current-context'] = kubeconfig_data['current-context']

                succeeded.append(cluster_name)
            else:
                failed.append((cluster_name, 'No config returned'))
        else:
            failed.append((cluster_name, f'{kubeconfig_response.status_code} - {kubeconfig_response.text}'))

    return succeeded, failed


def load_config(config_path):
    with open(config_path) as f:
        config = yaml.safe_load(f)
    urls = config.get('rancher_urls', [])
    if not urls:
        print(f"Error: 'rancher_urls' list is empty or missing in '{config_path}'")
        sys.exit(1)
    if not all(isinstance(u, str) for u in urls):
        print(f"Error: all entries in 'rancher_urls' must be strings")
        sys.exit(1)
    return urls


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Fetch kubeconfigs from Rancher instances')
    parser.add_argument('--config', default='rancher-endpoints.yaml', help='Path to config file (default: rancher-endpoints.yaml)')
    args = parser.parse_args()

    if not os.path.exists(args.config):
        print(f"Error: config file '{args.config}' not found")
        sys.exit(1)

    rancher_urls = load_config(args.config)

    username = input("Rancher username: ")
    password = getpass.getpass("Rancher password: ")

    skipped_instances = []

    for rancher_url in rancher_urls:
        print(f"\n{rancher_url}")
        token = get_rancher_token(rancher_url, username, password)
        if token is None:
            print(f"  Skipped (login failed).")
            skipped_instances.append(rancher_url)
            continue
        succeeded, failed = fetch_kubeconfigs_from_rancher(rancher_url, token)
        for name in succeeded:
            print(f"  + {name}")
        for name, reason in failed:
            print(f"  - {name} ({reason})")
        if not succeeded and not failed:
            print(f"  No clusters found.")

    print("")

    if skipped_instances:
        print(f"Skipped instances (login failure):")
        for url in skipped_instances:
            print(f"  - {url}")

    with open('combined-kubeconfig.yaml', 'w') as combined_file:
        yaml.dump(combined_kubeconfig, combined_file)

    print(f"\nCombined kubeconfig saved as 'combined-kubeconfig.yaml'.")
