#!/bin/bash

kubectl apply -f 00-shared-app-data-pvc.yaml

SERVICES="blob-gateway ams swap proxy"

for service in $SERVICES; do
  kubectl delete -f $service/02-deployment.yaml
  kubectl delete -f $service/03-ingress.yaml
done

for service in $SERVICES; do
  while true; do
    count=$(kubectl get pods -A | grep ${service}-service | wc -l)
    if [ $count -eq 0 ]; then
      break
    fi
    sleep 10
  done

  kubectl apply -f $service/02-deployment.yaml
  kubectl apply -f $service/03-ingress.yaml

  while true; do
    count=$(kubectl get pods -A | grep ${service}-service | grep Running | wc -l)
    if [ $count -eq 5 ]; then
      break
    fi
    sleep 10
  done
done
