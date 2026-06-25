# Rancher Kubeconfig Getter

Fetches Kubernetes kubeconfig files from one or more Rancher instances and merges them into a single `combined-kubeconfig.yaml`.

## Prerequisites

- Python 3.6+
- `pip install -r requirements.txt`

## Usage

Configure the Rancher URLs in `rancher-endpoints.yaml`:

```yaml
rancher_urls:
  - https://rancher.mycompany.net
  - https://rancher-test.mycompany.net
```

Run the script:

```bash
python rancher-kubeconfig-getter.py
```

You will be prompted for your Rancher username and password (same credentials are used for all instances). The script authenticates via Active Directory, discovers all clusters, generates a kubeconfig for each, and writes them to `combined-kubeconfig.yaml`.

Use a custom config path:

```bash
python rancher-kubeconfig-getter.py --config /path/to/endpoints.yaml
```

Use the output with kubectl:

```bash
kubectl --kubeconfig combined-kubeconfig.yaml get nodes
# or
export KUBECONFIG=./combined-kubeconfig.yaml
```

## Limitations

- Active Directory authentication only
- Same credentials for all Rancher instances
- Output always written to `combined-kubeconfig.yaml` in the current directory

## License

GPL-3.0
