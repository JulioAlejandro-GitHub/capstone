# Topología de ejecución
**Acordado:** control plane con servicios Docker y PostgreSQL; execution plane Docker o Python local, con GPU Metal cuando esté disponible.
**Verificar en código:** docker-compose, Makefile, `local_launch.py`, `campaign.py`, `worker.py`, configuración y reporter.
**No asumir:** que todos los comandos Python o pruebas deban correr en Docker.
**Fecha revisión documental:** 2026-10-16.
