#!/usr/bin/env bash
# Removes the spotify-crossplane example.
#
# The composite resources are deleted FIRST, while the provider, ProviderConfig
# and Secret are still present, so their REMOVE mappings run upstream (remove the
# track, then unfollow the playlist) before the provider is torn down. kubectl
# blocks on each delete until its finalizer clears.
#
# If a delete hangs (e.g. the Spotify token expired so REMOVE keeps failing),
# strip the finalizer to force it:
#   kubectl patch spotifyplaylist <name> -n default --type=merge -p '{"metadata":{"finalizers":[]}}'

# no `set -e`: keep going even if something is already gone
cd "$(dirname "${BASH_SOURCE[0]}")"

echo "==> Deleting example composite resources (triggers upstream cleanup)"
kubectl delete spotifyplaylistitem --all -n default --ignore-not-found
kubectl delete spotifyplaylist     --all -n default --ignore-not-found

echo "==> Deleting Compositions and XRDs"
kubectl delete -f k8s/playlist-item.yaml --ignore-not-found
kubectl delete -f k8s/playlist.yaml      --ignore-not-found

echo "==> Deleting ProviderConfig and Secret"
kubectl delete -f k8s/provider-config.yaml --ignore-not-found
kubectl delete secret spotify-access-token -n crossplane-system --ignore-not-found

echo "==> Deleting functions and provider-http"
kubectl delete -f k8s/functions.yaml --ignore-not-found
kubectl delete -f k8s/provider.yaml  --ignore-not-found

echo
echo "Done. Crossplane core is left installed."
echo "To remove it too: helm uninstall crossplane -n crossplane-system; kubectl delete ns crossplane-system"