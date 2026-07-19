# Deployment troubleshooting

`ExternalName ... is required` means a data service was disabled without its external
DNS name. Set both `enabled=false` and `externalHost`.

Pending PVCs usually indicate a missing StorageClass or unavailable capacity. Inspect
`kubectl describe pvc -n openmaster` and set the corresponding
`persistence.storageClassName`.

Migration hook failures are visible with `kubectl logs job/openmaster-openmaster-migrate
-n openmaster`. Verify `DATABASE_URL`, connectivity, and database permissions; do not
print the Secret.

DNS failures under NetworkPolicy usually mean the cluster's DNS labels differ from the
defaults. Inspect CoreDNS labels and update `networkPolicy.dns`. External database,
Redis, or MinIO timeouts require explicit destination CIDRs under
`networkPolicy.externalEgress`; ExternalName alone does not create an egress allowance.

Ingress 404 or timeout errors commonly indicate an incorrect ingress class, host, or
controller labels. Match `ingress.controllerNamespace` and
`ingress.controllerPodLabels` to the actual controller pods.

HPA showing unknown CPU utilization means metrics-server is unavailable or the target
workload lacks resource requests. The chart supplies requests; verify the metrics API.
