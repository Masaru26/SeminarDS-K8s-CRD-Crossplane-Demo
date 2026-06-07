#!/usr/bin/env bash
# Deploys the spotify-crossplane example onto the current kube-context.
#
# Prerequisites:
#   - kubectl, helm and python on PATH, pointing at a running cluster (e.g. minikube)
#   - python deps for refresh_token.py (requests, python-dotenv)
#   - a .env file (next to this script) with CLIENT_ID, CLIENT_SECRET and REFRESH_TOKEN
#     (run `python refresh_token.py` once without REFRESH_TOKEN to bootstrap it)
#
# Note: if the provider-http pod CrashLoops on a "customresourcedefinitions ...
# is forbidden" error, apply ../poc-crossplane-simpel/install/30-provider-http-extra-rbac.yml
# and restart the provider deployment.

set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")"

PY="$(command -v python3 || command -v python)"

echo "==> Installing Crossplane core (idempotent)"
helm repo add crossplane-stable https://charts.crossplane.io/stable >/dev/null
helm repo update >/dev/null
helm upgrade --install crossplane crossplane-stable/crossplane \
  --namespace crossplane-system --create-namespace --version 2.3.1 --wait

echo "==> Installing provider-http and composition functions"
kubectl apply -f k8s/provider.yaml
kubectl apply -f k8s/functions.yaml

echo "==> Waiting for the provider and functions to become Healthy"
kubectl wait --for=condition=Healthy --timeout=300s provider.pkg.crossplane.io/provider-http
kubectl wait --for=condition=Healthy --timeout=300s function.pkg.crossplane.io --all

echo "==> Writing the Spotify access-token Secret (refresh_token.py)"
"$PY" refresh_token.py
if ! kubectl get secret spotify-access-token -n crossplane-system >/dev/null 2>&1; then
  echo "ERROR: Secret 'spotify-access-token' was not created. Set REFRESH_TOKEN in .env" >&2
  echo "       (run 'python refresh_token.py' once to bootstrap it), then re-run." >&2
  exit 1
fi

echo "==> Applying the ProviderConfig"
kubectl apply -f k8s/provider-config.yaml

echo "==> Applying XRDs and Compositions"
kubectl apply -f k8s/playlist.yaml
kubectl apply -f k8s/playlist-item.yaml
kubectl wait --for=condition=Established --timeout=120s \
  crd/spotifyplaylists.music.example.org \
  crd/spotifyplaylistitems.music.example.org

echo "==> Applying the example resources"
kubectl apply -f k8s/example-resources.yaml

echo
echo "Done. Watch the resources reconcile with:"
echo "  kubectl get spotifyplaylist,spotifyplaylistitem,requests.http.m.crossplane.io -n default"
