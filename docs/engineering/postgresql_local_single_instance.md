# PostgreSQL local: instancia única

Capstone usa exclusivamente PostgreSQL 17 instalado en el host y la base persistente
identificada como `malaria_experiments`. Ese nombre es el equivalente real de Capstone y no
se renombra automáticamente. Backend y frontend se ejecutan directamente en macOS.
Docker no forma parte de la arquitectura operativa ni de los criterios de aprobación del
Capstone.

Solo existe el ambiente operativo `development`. Las pruebas usan la misma base mediante
transacciones revertidas; un schema `capstone_test_*` es una excepción temporal, no otro
ambiente ni otra base.
