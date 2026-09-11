# E4 — Compatibilidad de head_units y diagnóstico de aserciones

HEAD: `6b24d50ad24ea641e70e7c8b758cc93c79729d7e`. Se preservaron el árbol y los informes anteriores. Dictamen: **NO APROBADA**.

El usuario ejecutó la prueba acotada y obtuvo una AssertionError sanitizada en 0,42 s. Esa salida no permite determinar qué aserción falló. La revisión local de las doce configuraciones sintéticas revela una incompatibilidad comprobable: el resolver E2 produce `head_units=0` para las cuatro configuraciones DenseNet121, mientras `campaign_configuration_valid` exigía un entero >=1. Custom CNN produce 128 y VGG16 1024. No se ejecutaron ni construyeron modelos para obtener esa evidencia.

Se corrigió únicamente el mínimo de head_units en la revisión 02 a cero: un entero no negativo admite la configuración vigente de DenseNet121. No se elimina el campo ni su validación de tipo. Se añadieron cuatro casos SQL negativos para -1, JSON null, true y la cadena "0". La prueba acotada conserva las aserciones anteriores y valida las doce configuraciones completas, pero ahora identifica explícitamente el paso que falla: expresión antigua, expresión corregida o configuración:modelo:optimizador. Sólo se imprimen identificadores del fixture sintético; no se revelan parámetros operativos ni mensajes del driver.

Esto demuestra un defecto del validador por inspección y contraste con el resolver, pero aún no demuestra que explique la AssertionError concreta ni que la integración esté resuelta. No se aplicó ninguna migración operativa; 01 se conserva intacta.

Validación local: **77 aprobadas, 50 PostgreSQL omitidas**, dos avisos existentes Alembic. Ruff aprobado. La suite PostgreSQL tiene ahora **49 casos sintéticos y uno de instalación pública**. El intento de ejecutar la prueba acotada por Compose sigue fallando por acceso denegado a Docker API. No hay nueva evidencia de ejecución PostgreSQL desde esta sesión.

Repetir primero el mismo comando acotado comunicado por el usuario. Si pasa, ejecutar `tests/test_campaigns_postgres.py -k 'not public_migration_readonly'` con el mismo opt-in Compose; esperado 49 aprobadas y una deseleccionada. No iniciar instalación operativa, E5 o entrenamientos. Manifiesto efectivo: `etapa_4_manifiesto_head_units_2026-09-11.json`.

Renderizado offline en memoria de ambos upgrade(): 44673 bytes; SHA-256 `e767446ae9a7a092cde6844392f372ace62626a1c34048ea755757374c5fd1b0`. No acredita ejecución PostgreSQL.
