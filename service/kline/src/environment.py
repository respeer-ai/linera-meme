import os

def running_in_k8s():
    return "KUBERNETES_SERVICE_HOST" in os.environ
