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

## Worker logs show Redis connection refused after deployment

On an older chart, Celery can start a few seconds before the Redis container accepts
connections. Celery retries automatically, so historical `Connection refused` entries
do not prove that the current worker is disconnected. Confirm the latest state with:

```bash
kubectl logs deployment/openmaster-openmaster-analysis-worker \
  -n openmaster --since=2m
```

The current chart prevents this startup race with a bounded `wait-for-broker` init
container. After upgrading the API/worker image and chart, check it with:

```bash
kubectl get pod -n openmaster \
  -l app.kubernetes.io/component=analysis-worker \
  -o jsonpath='{.items[0].status.initContainerStatuses[0].state.terminated.reason}{"\n"}'
```

The expected value is `Completed`. If it remains pending, inspect Redis itself and the
init-container log:

```bash
kubectl logs -n openmaster \
  -l app.kubernetes.io/component=analysis-worker \
  -c wait-for-broker --tail=100
```

## A deliberately unknown job returns 404

`/api/v1/analysis-jobs/inexistant` is a negative test and must return 404. Because
`curl -f` turns 4xx responses into exit code 22, use `curl -sk` when you want to see
the JSON error body. Test a real workflow with the UUID returned by the POST request.
PostgreSQL additionally uses a short-lived, capability-limited init container to assign
the persistent volume to UID/GID `70`; the database process itself remains non-root.
