# DBV2.3 — BD-V2 PERSISTENTE CERTIFICADA

Estado técnico PASS; pendiente **GATE DBV2.3**. **BD-V2 PERSISTE PARA DBV2.4**. No se autoriza ni ejecuta transferencia en esta fase.

| Propiedad | Resultado |
|---|---|
| PostgreSQL | 17.9, server_version_num 170009 |
| Database | capstone_v2_isolated_persistent |
| Host lógico / acceso local | capstone_db_v2 / 127.0.0.1:56440 |
| Volumen persistente | capstone_v2_isolated_persistent_data |
| Alembic revision / head | pg_v2_baseline |
| down_revision / roots / heads | None / 1 / 1 |
| Tablas aplicación / técnica | 104 / 1 |
| Views / FK / CHECK / UNIQUE | 33 / 251 / 518 / 77 |
| Índices aplicación / adicionales UNIQUE / físicos | 413 / 41 / 414 |
| Funciones propias / triggers | 79 / 105 |
| Extensiones | pgcrypto 1.3, plpgsql 1.0 |
| Tablas XAI | 9; R1 y E-04 intactos |
| clinical_target_recall | numeric NOT NULL; sin DEFAULT; (0,1] |
| Reinicio / fixtures remanentes | PASS / 0 |
| Dataset inspeccionadas / directas / manejo técnico / semántico | 13 / 12 / 1 / 0 |
| Usuario inspeccionadas / directas / manejo técnico / semántico | 3 / 3 / 0 / 0 |
| Dependencias inesperadas | Ninguna |
| Escrituras origen / datos reales transferidos / cutover | 0 / 0 / NO |

Manifest estructural: `15c95e0c047c7cc29397635130ddb0a1f6820eab6d4c746f7078fb9f8bb3eafb`.
Revisión raíz: `e3aaad12e49e65cff8ad9742fcdd83af075f2e2fcfaa81733a2bec121efef279`.

La instalación partió de catálogo vacío y utilizó únicamente Alembic v2. Coinciden identidad, definición y ACL de las 18 categorías del manifest DBV2.2; no se aprobó por conteos solamente. El mismo contenedor, cluster, base y volumen sobreviven a stop/start. El servicio permanece activo con restart policy unless-stopped.

La matriz contiene 177 columnas explícitas. La excepción técnica es el ciclo transitorio FROZEN→VALIDATED→FROZEN autorizado en DBV2.1; estado final y timestamps originales se preservan, con FK/triggers activos. Se probó con fixture sintético siempre revertido. No cambia split, labels, IDs, hashes, rutas ni fingerprints.

El origen confirmó 27.558 muestras, TRAIN 22.180 / VAL 2.693 / TEST 2.685 y 201 pacientes. dataset_split_images conserva 55.116 filas en dos raíces físicas; sus dataset_version_id son NULL en el origen y se conservarán NULL. No se deduplica ni se reconstruye ningún enlace.

El usuario existente es uno activo, con una asignación de rol. Se inspeccionaron sólo metadatos de credenciales; nunca se leyeron valores password_hash. La copia futura conserva exactamente el valor. Hay cinco definiciones de rol en origen; el plan selecciona sólo el rol referenciado por user_roles.

[Persistencia](dbv2_3_persistent_database.md) · [Estructura](dbv2_3_structural_certification.md) · [READ ONLY](dbv2_3_source_readonly.md) · [Compatibilidad](dbv2_3_insert_select_compatibility.md) · [Plan no ejecutado](dbv2_4_transfer_plan.sql).

No se modificaron revisión raíz, manifest de recursos ni ningún SQL certificado. La única adaptación del sobre de instalación es alembic_v2/safety.py: reconoce la autorización DBV2.3, exige etiquetas persistent y PostgreSQL 17.9. No modifica el catálogo ni crea una revisión.

**No eliminar esta base ni su volumen, no reconstruirla: es el destino DBV2.4.** No se inició DBV2.4, freeze final, SW-v2 ni cutover. Solicitud: **GATE DBV2.3**.
