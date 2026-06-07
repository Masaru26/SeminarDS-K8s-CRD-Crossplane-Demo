#!/usr/bin/env bash
set -euo pipefail

helm repo add crossplane-stable https://charts.crossplane.io/stable
helm repo update

helm upgrade --install crossplane crossplane-stable/crossplane \
  --namespace crossplane-system --create-namespace \
  --version 2.3.1

kubectl wait --for=condition=Available \
  -n crossplane-system deploy/crossplane deploy/crossplane-rbac-manager
