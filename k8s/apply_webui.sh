#!/bin/bash

kubectl delete -f webui/02-deployment.yaml
kubectl apply -f webui/02-deployment.yaml

