#!/bin/bash

helm upgrade --install supply-chain-perspective ./charts/openshift-console-plugin \
  --namespace supply-chain-dashboard \
  --set plugin.name=supply-chain-perspective \
  --set plugin.image=quay.io/robertsandoval/supply-chain-perspective:latest
