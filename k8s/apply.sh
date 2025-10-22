#!/bin/bash

kubectl apply -f 00-shared-app-data-pvc.yaml

SERVICES="blob-gateway ams swap proxy"
SERVICES="proxy"

if [ -z "$MYSQL_ROOT_PASSWORD" -o -z "$MYSQL_PASSWORD" ]; then
  echo "Error: SET MYSQL_ROOT_PASSWORD AND MYSQL_PASSWORD"
  exit 1
fi

for service in $SERVICES; do
  kubectl delete -f $service/02-deployment.yaml
  kubectl delete -f $service/03-ingress.yaml
done

wait_pods() {
  pod_name=$1
  replicas=$2
  status=$3

  while true; do
    count=$(kubectl get pods -A | grep $pod_name | grep "$status" | wc -l)
    if [ $count -eq $replicas ]; then
      break
    fi
    sleep 10
  done
}

for service in $SERVICES; do
  wait_pods ${service}-service 0 ""

  kubectl apply -f $service/01-strip-prefix.yaml
  kubectl apply -f $service/02-deployment.yaml
  kubectl apply -f $service/03-ingress.yaml

  wait_pods ${service}-service 5 Running
done

count=$(kubectl get secret -n kube-system mysql-secret | grep mysql | wc -l)
if [ $count -eq 0 ]; then
  kubectl create secret generic mysql-secret --from-literal=MYSQL_ROOT_PASSWORD="$MYSQL_ROOT_PASSWORD" --from-literal=MYSQL_PASSWORD="$MYSQL_PASSWORD" --namespace kube-system
fi

kubectl delete -f mysql/02-deployment.yaml

wait_pods mysql-service 0 ""

kubectl apply -f mysql/00-user.yaml
kubectl apply -f mysql/01-pvc.yaml
kubectl apply -f mysql/02-deployment.yaml

wait_pods msyql-service 1 Running

kubectl delete -f kline/02-deployment.yaml
kubectl delete -f kline/03-ingress.yaml

wait_pods kline-service 0 ""

kubectl apply -f kline/01-strip-prefix.yaml
kubectl apply -f kline/02-deployment.yaml
kubectl apply -f kline/03-ingress.yaml

wait_pods kline-service 1 Running

kubectl delete -f funder/02-deployment.yaml

wait_pods funder-service 0 ""

kubectl apply -f funder/02-deployment.yaml

wait_pods funder-service 1 Running

kubectl delete -f maker/02-deployment.yaml

wait_pods maker-service 0 ""
wait_pods maker-wallet-service 0 ""

kubectl apply -f maker/01-pvc.yaml
kubectl apply -f maker/02-deployment.yaml

wait_pods maker-service 1 Running
wait_pods maker-wallet-service 1 Running

####
## Replace CHAIN_ID and APPLICATION_ID in webui
####
echo "Please submit webui, generate docker images then apply webui separately"
