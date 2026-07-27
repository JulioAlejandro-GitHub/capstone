# Validación de datos científicos

La validación se aplica en tres capas:

1. Pydantic rechaza campos extra, enums, SHA-256, tamaños y dimensiones.
2. El servicio valida padres existentes/no archivados, transiciones y dependencias.
3. PostgreSQL protege FK, unicidad, cronología, JSON objeto y coherencia de archivado.

Transiciones:

- caso: draft → registered → ready; ready puede volver a registered;
- muestra: registered → received → prepared;
- frotis: registered → prepared → ready_for_capture; ready puede volver a prepared;
- imagen: registered → available/unavailable/rejected; available y unavailable pueden
  alternar; rejected es terminal;
- archived es terminal para todas las entidades.

Archivar un sujeto/caso/muestra/frotis con hijos activos produce 409. Una imagen puede
archivarse directamente. No se aplica cascada.

Las pruebas PostgreSQL usan transacción exterior y savepoints por request; el rollback final
elimina usuarios, entidades y eventos. Una constraint de test provoca un fallo real al
insertar `audit_events` y demuestra que la mutación también se revierte.

Prompt 4 añade checks e índices parciales de origen, estados, conteos, canales,
secuencias e identidades externas. La validación binaria está en
`image_security_validation.md`.
