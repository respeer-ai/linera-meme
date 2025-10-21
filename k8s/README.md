# Install efs driver at first

helm repo add aws-efs-csi-driver https://kubernetes-sigs.github.io/aws-efs-csi-driver/
helm repo update
helm install aws-efs-csi-driver aws-efs-csi-driver/aws-efs-csi-driver --namespace kube-system

# Add EFS-CSI-Policy role to EC2

# Create mysql secret

kubectl create secret generic mysql-secret \
  --from-literal=MYSQL_ROOT_PASSWORD="$MYSQL_ROOT_PASSWORD" \
  --from-literal=MYSQL_PASSWORD="$MYSQL_PASSWORD" \
  --namespace kube-system
