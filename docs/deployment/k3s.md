# k3s deployment

Install a supported k3s release (Kubernetes 1.26 or newer) with a working default
StorageClass and an ingress controller. Create and label the namespace before the
secret is synchronized:

```bash
kubectl create namespace openmaster
kubectl label namespace openmaster openmaster.io/secrets=enabled
kubectl get storageclass
kubectl get ingressclass
```

Copy `helm/openmaster/values-production.yaml` to a private environment-specific values
file. Replace the domain and TLS Secret name, select storage classes and sizes, set
immutable image references, and configure external service hosts/CIDRs if applicable.
Do not put credentials in a values file.

After configuring Vault as documented alongside this guide, run
`deployment/scripts/preflight-check.sh` and `deployment/scripts/deploy.sh`. The chart
performs Alembic migration as a serialized pre-install/pre-upgrade hook and waits for
all workloads. CPU-based autoscaling requires metrics-server, included by default in
normal k3s installations.

The default ingress selectors allow Traefik pods in `kube-system`. Change
`ingress.controllerNamespace` and `ingress.controllerPodLabels` for another controller.
