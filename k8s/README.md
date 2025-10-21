# Install efs driver at first

helm repo add aws-efs-csi-driver https://kubernetes-sigs.github.io/aws-efs-csi-driver/
helm repo update
helm install aws-efs-csi-driver aws-efs-csi-driver/aws-efs-csi-driver --namespace kube-system

# Add EFS-CSI-Policy role to EC2
