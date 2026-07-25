# Deployment troubleshooting

`ExternalName ... is required` means a data service was disabled without its external
DNS name. Set both `enabled=false` and `externalHost`.

Pending PVCs usually indicate a missing StorageClass or unavailable capacity. Inspect
`kubectl describe pvc -n openmaster` and set the corresponding
`persistence.storageClassName`.

Migration hook failures are visible with `kubectl logs job/openmaster-openmaster-migrate
-n openmaster`. Verify `DATABASE_URL`, connectivity, and database permissions; do not
print the Secret.

A first-install migration ending with `DeadlineExceeded` can indicate an outdated chart
that used a `pre-install` hook before internal PostgreSQL existed. Current charts use
`post-install,pre-upgrade`. Verify with `helm template` and update the checkout before
retrying.

DNS failures under NetworkPolicy usually mean the cluster's DNS labels differ from the
defaults. Inspect CoreDNS labels and update `networkPolicy.dns`. External database,
Redis, or MinIO timeouts require explicit destination CIDRs under
`networkPolicy.externalEgress`; ExternalName alone does not create an egress allowance.

Ingress 404 or timeout errors commonly indicate an incorrect ingress class, host, or
controller labels. Match `ingress.controllerNamespace` and
`ingress.controllerPodLabels` to the actual controller pods.

HPA showing unknown CPU utilization means metrics-server is unavailable or the target
workload lacks resource requests. The chart supplies requests; verify the metrics API.

`container has runAsNonRoot and image will run as root` on an internal data service
means an older chart applied the generic application security context to an official
data-service image. Current values set the documented runtime UID/GID explicitly for
PostgreSQL, Redis, and MinIO; PostgreSQL also receives a writable runtime socket volume.
PostgreSQL additionally uses a short-lived, capability-limited init container to assign
the persistent volume to UID/GID `70`; the database process itself remains non-root.
