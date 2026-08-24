# PostgreSQL local: instancia única

Capstone usa exclusivamente PostgreSQL 17 instalado en el host y la base persistente
identificada como `malaria_experiments`. Ese nombre es el equivalente real de Capstone y no
se renombra automáticamente. Backend y frontend se ejecutan directamente en
macOS. Docker no es parte del runtime ni de los criterios de aprobación
oficiales. Los artefactos Compose y Dockerfiles versionados son entrypoints
opcionales y no crean, reconstruyen o detienen la base oficial.

Solo existe el ambiente operativo `development`. Las pruebas usan la misma base mediante
transacciones revertidas; un schema `capstone_test_*` es una excepción temporal, no otro
ambiente ni otra base.
