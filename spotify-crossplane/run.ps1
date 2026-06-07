#!/usr/bin/env pwsh
# Deploys the spotify-crossplane example onto the current kube-context.
#
# Prerequisites:
#   - kubectl, helm and python on PATH, pointing at a running cluster (e.g. minikube)
#   - python deps for refresh_token.py (requests, python-dotenv)
#   - a .env file (next to this script) with CLIENT_ID, CLIENT_SECRET and REFRESH_TOKEN
#     (run `python refresh_token.py` once without REFRESH_TOKEN to bootstrap it)
#
# Note: if the provider-http pod CrashLoops on a "customresourcedefinitions ...
# is forbidden" error, apply ../poc-crossplane/install/02-provider-http-extra-rbac.yml
# and restart the provider deployment.

$ErrorActionPreference = "Stop"
Push-Location $PSScriptRoot
try {
    Write-Host "==> Installing Crossplane core (idempotent)" -ForegroundColor Cyan
    helm repo add crossplane-stable https://charts.crossplane.io/stable | Out-Null
    helm repo update | Out-Null
    helm upgrade --install crossplane crossplane-stable/crossplane `
        --namespace crossplane-system --create-namespace --version 2.3.1 --wait

    Write-Host "==> Installing provider-http and composition functions" -ForegroundColor Cyan
    kubectl apply -f k8s/01-provider.yaml
    kubectl apply -f k8s/02-functions.yaml

    Write-Host "==> Waiting for the provider and functions to become Healthy" -ForegroundColor Cyan
    kubectl wait --for=condition=Healthy --timeout=300s provider.pkg.crossplane.io/provider-http
    kubectl wait --for=condition=Healthy --timeout=300s function.pkg.crossplane.io --all

    Write-Host "==> Writing the Spotify access-token Secret (refresh_token.py)" -ForegroundColor Cyan
    python refresh_token.py
    kubectl get secret spotify-access-token -n crossplane-system 2>$null | Out-Null
    if ($LASTEXITCODE -ne 0) {
        throw "Secret 'spotify-access-token' was not created. Set REFRESH_TOKEN in .env " +
              "(run 'python refresh_token.py' once to bootstrap it), then re-run."
    }

    Write-Host "==> Applying the ProviderConfig" -ForegroundColor Cyan
    kubectl apply -f k8s/03-provider-config.yaml

    Write-Host "==> Applying XRDs and Compositions" -ForegroundColor Cyan
    kubectl apply -f k8s/04-playlist.yaml
    kubectl apply -f k8s/05-playlist-item.yaml
    kubectl wait --for=condition=Established --timeout=120s `
        crd/spotifyplaylists.music.example.org `
        crd/spotifyplaylistitems.music.example.org

    Write-Host "==> Applying the example resources" -ForegroundColor Cyan
    kubectl apply -f k8s/06-example-resources.yaml

    Write-Host ""
    Write-Host "Done. Watch the resources reconcile with:" -ForegroundColor Green
    Write-Host "  kubectl get spotifyplaylist,spotifyplaylistitem,requests.http.m.crossplane.io -n default"
}
finally {
    Pop-Location
}