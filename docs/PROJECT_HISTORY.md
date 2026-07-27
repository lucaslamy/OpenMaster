# Project history and pre-master decision

OpenMaster retains uploaded sources and rendered masters under immutable MinIO object
keys. PostgreSQL retains analysis, settings, status, render lineage, and visualization
data. The studio lists the twenty newest root projects; final-render child jobs remain
attached to their parent and do not consume history slots.

No application cleanup removes these objects. Production MinIO lifecycle rules must
not expire `analysis/` or `mastering/` objects belonging to the newest twenty database
projects. Backups and capacity monitoring remain operational responsibilities.

The lifecycle is:

1. choose a local file;
2. validate the password before transfer;
3. upload the source to MinIO;
4. run and persist Celery analysis;
5. stop in `analyzed`;
6. stream the retained source through live browser DSP;
7. persist settings and atomically enter `mastering`;
8. render locally or through RunPod without repeating analysis;
9. retain and expose the downloadable master.

Repeated decision requests cannot enqueue the same analysed project twice because the
database transition from `analyzed` to `mastering` is conditional and atomic.
