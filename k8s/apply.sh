#!/bin/bash

kubectl apply -f 00-shared-app-data-pvc.yaml

SERVICES="blob-gateway ams swap proxy"

export FAUCET_URL=https://faucet.testnet-conway.linera.net
# export FAUCET_URL=http://local-genesis-service:8080

RE_GENERATE=0

count=$(kubectl get secret -n kube-system mysql-secret | grep mysql | wc -l)
if [ $count -eq 0 ]; then
  if [ -z "$MYSQL_ROOT_PASSWORD" -o -z "$MYSQL_PASSWORD" ]; then
    echo "Error: SET MYSQL_ROOT_PASSWORD AND MYSQL_PASSWORD"
    exit 1
  fi

  kubectl create secret generic mysql-secret --from-literal=MYSQL_ROOT_PASSWORD="$MYSQL_ROOT_PASSWORD" --from-literal=MYSQL_PASSWORD="$MYSQL_PASSWORD" --namespace kube-system
fi

wait_pods() {
  pod_name=$1
  replicas=$2
  status=$3

  while true; do
    count=$(kubectl get pods -A | grep $pod_name | grep "$status" | wc -l)
    if [ $count -eq $replicas ]; then
      break
    fi
    echo "Waiting for $pod_name be $status"
    sleep 10
  done
}

kline_pod_name=$(kubectl get pods -A | grep kline | awk '{print $2}')
if [ $RE_GENERATE -eq 1 -a ! -z "$kline_pod_name" ]; then
  kubectl exec -it $kline_pod_name -n kube-system -- sh -c "rm -vrf /shared-app-data/*"
fi

for service in $SERVICES; do
  envsubst '$FAUCET_URL' < $service/02-deployment.yaml | kubectl delete -f -
  envsubst '$FAUCET_URL' < $service/03-ingress.yaml | kubectl delete -f -
done

envsubst '$FAUCET_URL' < mysql/02-deployment.yaml | kubectl delete -f -

wait_pods mysql-service 0 ""

envsubst '$FAUCET_URL' < kline/02-deployment.yaml | kubectl delete -f -
envsubst '$FAUCET_URL' < kline/03-ingress.yaml | kubectl delete -f -

wait_pods kline-service 0 ""

envsubst '$FAUCET_URL' < funder/02-deployment.yaml | kubectl delete -f -

wait_pods funder-service 0 ""

envsubst '$FAUCET_URL' < maker/02-deployment.yaml | kubectl delete -f -

wait_pods maker-service 0 ""
wait_pods maker-wallet-service 0 ""

for service in $SERVICES; do
  wait_pods ${service}-service 0 ""

  envsubst '$FAUCET_URL' < $service/01-strip-prefix.yaml | kubectl apply -f -
  envsubst '$FAUCET_URL' < $service/02-deployment.yaml | kubectl apply -f -
  envsubst '$FAUCET_URL' < $service/03-ingress.yaml | kubectl apply -f -

  wait_pods ${service}-service 5 Running
done

envsubst '$FAUCET_URL' < mysql/00-user.yaml | kubectl apply -f -
envsubst '$FAUCET_URL' < mysql/01-pvc.yaml | kubectl apply -f -
envsubst '$FAUCET_URL' < mysql/02-deployment.yaml | kubectl apply -f -

wait_pods mysql-service 1 Running

envsubst '$FAUCET_URL' < kline/01-strip-prefix.yaml | kubectl apply -f -
envsubst '$FAUCET_URL' < kline/02-deployment.yaml | kubectl apply -f -
envsubst '$FAUCET_URL' < kline/03-ingress.yaml | kubectl apply -f -

wait_pods kline-service 1 Running

envsubst '$FAUCET_URL' < funder/02-deployment.yaml | kubectl apply -f -

wait_pods funder-service 1 Running

envsubst '$FAUCET_URL' < maker/00-strip-prefix.yaml | kubectl apply -f -
envsubst '$FAUCET_URL' < maker/02-deployment.yaml | kubectl apply -f -
envsubst '$FAUCET_URL' < maker/03-ingress.yaml | kubectl apply -f -

wait_pods maker-service 1 Running
wait_pods maker-wallet-service 1 Running

####
## Replace CHAIN_ID and APPLICATION_ID in webui
####
echo "Please submit webui, generate docker images then apply webui separately"

BLOB_GATEWAY_CHAIN_ID=$(kubectl exec -it blob-gateway-service-0 -n kube-system -- cat /shared-app-data/BLOB_GATEWAY_MULTI_OWNER_CHAIN_ID | tr -d '\r\n')
BLOB_GATEWAY_APPLICATION_ID=$(kubectl exec -it blob-gateway-service-0 -n kube-system -- cat /shared-app-data/BLOB_GATEWAY_APPLICATION_ID | tr -d '\r\n')

AMS_CHAIN_ID=$(kubectl exec -it blob-gateway-service-0 -n kube-system -- cat /shared-app-data/AMS_MULTI_OWNER_CHAIN_ID | tr -d '\r\n')
AMS_APPLICATION_ID=$(kubectl exec -it blob-gateway-service-0 -n kube-system -- cat /shared-app-data/AMS_APPLICATION_ID | tr -d '\r\n')

PROXY_CHAIN_ID=$(kubectl exec -it blob-gateway-service-0 -n kube-system -- cat /shared-app-data/PROXY_MULTI_OWNER_CHAIN_ID | tr -d '\r\n')
PROXY_APPLICATION_ID=$(kubectl exec -it blob-gateway-service-0 -n kube-system -- cat /shared-app-data/PROXY_APPLICATION_ID | tr -d '\r\n')

SWAP_CHAIN_ID=$(kubectl exec -it blob-gateway-service-0 -n kube-system -- cat /shared-app-data/SWAP_MULTI_OWNER_CHAIN_ID | tr -d '\r\n')
SWAP_APPLICATION_ID=$(kubectl exec -it blob-gateway-service-0 -n kube-system -- cat /shared-app-data/SWAP_APPLICATION_ID | tr -d '\r\n')

SCRIPT_DIR=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )
ROOT_DIR=$SCRIPT_DIR/..
DOMAIN_FILE="${ROOT_DIR}/webui/src/constant/domain.ts"

cat <<EOF > $DOMAIN_FILE
export const SUB_DOMAIN = 'testnet-conway.'
export const BLOB_GATEWAY_CHAIN_ID = '$BLOB_GATEWAY_CHAIN_ID'
export const BLOB_GATEWAY_APPLICATION_ID = '$BLOB_GATEWAY_APPLICATION_ID'
export const AMS_CHAIN_ID = '$AMS_CHAIN_ID'
export const AMS_APPLICATION_ID = '$AMS_APPLICATION_ID'
export const PROXY_CHAIN_ID = '$PROXY_CHAIN_ID'
export const PROXY_APPLICATION_ID = '$PROXY_APPLICATION_ID'
export const SWAP_CHAIN_ID = '$SWAP_CHAIN_ID'
export const SWAP_APPLICATION_ID = '$SWAP_APPLICATION_ID'
EOF
