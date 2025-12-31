#!/bin/bash

export FAUCET_URL=https://faucet.testnet-conway.linera.net
# export FAUCET_URL=http://local-genesis-service:8080
export REPLICAS=${REPLICAS:-5}
export MAKER_REPLICAS=${MAKER_REPLICAS:-3}
export DEPLOY_MYSQL=${DEPLOY_MYSQL:-1}
export SHARED_APP_DATA_STORAGE_CLASS=${SHARED_APP_DATA_STORAGE_CLASS:-efs-storage-class}

export RE_GENERATE=${RE_GENERATE:-0}
export AUTO_RUN=${AUTO_RUN:-0}

if [ $RE_GENERATE -eq 1 ]; then
  SERVICES="blob-gateway ams swap proxy"
else
  SERVICES="swap proxy blob-gateway ams"
fi

if [ $DEPLOY_MYSQL -eq 1 ]; then
  count=$(kubectl get secret -n kube-system mysql-password-secret | grep mysql | wc -l)
  if [ $count -eq 0 ]; then
    if [ -z "$MYSQL_ROOT_PASSWORD" -o -z "$MYSQL_PASSWORD" ]; then
      echo "Error: SET MYSQL_ROOT_PASSWORD AND MYSQL_PASSWORD"
      exit 1
    fi

    kubectl create secret generic mysql-password-secret --from-literal=MYSQL_ROOT_PASSWORD="$MYSQL_ROOT_PASSWORD" --from-literal=MYSQL_PASSWORD="$MYSQL_PASSWORD" --namespace kube-system
  fi
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

ask_yes_no() {
  if [ $AUTO_RUN -eq 1 ]; then
    echo "yes"
    return 0
  fi

  local label="$1"
  local choice

  echo "$label" >&2

  select choice in yes no; do
    case "$choice" in
      yes)
        echo "yes"
        return 0
        ;;
      no)
        echo "no"
        return 0
        ;;
      *)
        echo "Please choose 1 or 2."
        ;;
    esac
  done
}

if [ $RE_GENERATE -eq 1 ]; then
  result=$(ask_yes_no "Continue delete application data ?")
  echo $result
  if [ "$result" == "yes" ]; then
    echo "Deleting application data now ..."
  else
    echo "Exiting ..."
    exit 0
  fi

  kline_pod_name=$(kubectl get pods -A | grep kline | awk '{print $2}')
  if [ ! -z "$kline_pod_name" ]; then
    kubectl exec -it $kline_pod_name -n kube-system -- sh -c "rm -vrf /shared-app-data/*"
  else
    echo "Cannot find kline pod, failed to delete application data."
    result=$(ask_yes_no "Continue deploy applications ?")
    echo $result
    if [ "$result" == "yes" ]; then
      echo "Deploy application now ..."
    else
      echo "Exiting ..."
      exit 0
    fi
  fi
fi

for service in $SERVICES; do
  envsubst '$FAUCET_URL $REPLICAS' < $service/02-deployment.yaml | kubectl delete -f -
  envsubst '$FAUCET_URL $REPLICAS' < $service/03-ingress.yaml | kubectl delete -f -
done


if [ $DEPLOY_MYSQL -eq 1 ]; then
  envsubst '$FAUCET_URL $REPLICAS' < mysql/02-deployment.yaml | kubectl delete -f -

  wait_pods mysql-service 0 ""
fi

envsubst '$FAUCET_URL $REPLICAS' < kline/02-deployment.yaml | kubectl delete -f -
envsubst '$FAUCET_URL $REPLICAS' < kline/03-ingress.yaml | kubectl delete -f -

wait_pods kline-service 0 ""

envsubst '$FAUCET_URL $REPLICAS' < funder/02-deployment.yaml | kubectl delete -f -

wait_pods funder-service 0 ""

envsubst '$FAUCET_URL $REPLICAS' < maker/02-deployment.yaml | kubectl delete -f -

wait_pods maker-service 0 ""
wait_pods maker-wallet-service 0 ""

envsubst '$SHARED_APP_DATA_STORAGE_CLASS' < 00-shared-app-data-pvc.yaml | kubectl apply -f -

for service in $SERVICES; do
  wait_pods ${service}-service 0 ""

  envsubst '$FAUCET_URL $REPLICAS' < $service/01-strip-prefix.yaml | kubectl apply -f -
  envsubst '$FAUCET_URL $REPLICAS' < $service/02-deployment.yaml | kubectl apply -f -
  envsubst '$FAUCET_URL $REPLICAS' < $service/03-ingress.yaml | kubectl apply -f -

  wait_pods ${service}-service $REPLICAS Running
done

envsubst '$FAUCET_URL $REPLICAS' < mysql/00-user.yaml | kubectl apply -f -
if [ $DEPLOY_MYSQL -eq 1 ]; then
  envsubst '$FAUCET_URL $REPLICAS' < mysql/01-pvc.yaml | kubectl apply -f -
  envsubst '$FAUCET_URL $REPLICAS' < mysql/02-deployment.yaml | kubectl apply -f -

  wait_pods mysql-service 1 Running
fi

envsubst '$FAUCET_URL $REPLICAS' < kline/01-strip-prefix.yaml | kubectl apply -f -
envsubst '$FAUCET_URL $REPLICAS' < kline/02-deployment.yaml | kubectl apply -f -
envsubst '$FAUCET_URL $REPLICAS' < kline/03-ingress.yaml | kubectl apply -f -

wait_pods kline-service 1 Running

envsubst '$FAUCET_URL $REPLICAS' < funder/02-deployment.yaml | kubectl apply -f -

wait_pods funder-service 1 Running

envsubst '$FAUCET_URL' < maker/00-strip-prefix.yaml | kubectl apply -f -
envsubst '$FAUCET_URL $MAKER_REPLICAS' < maker/02-deployment.yaml | kubectl apply -f -
envsubst '$FAUCET_URL' < maker/03-ingress.yaml | kubectl apply -f -

wait_pods maker-service $MAKER_REPLICAS Running
wait_pods maker-wallet-service $MAKER_REPLICAS Running

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
DOMAIN_FILE="${ROOT_DIR}/webui-v2/src/constant/domain.ts"

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
