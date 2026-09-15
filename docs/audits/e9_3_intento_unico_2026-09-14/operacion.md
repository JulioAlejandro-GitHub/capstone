# Seguimiento del único intento autorizado

Campaña pausada `3acf89b7-dc42-4b7a-8e2a-ca6ea024c344`.
Dataset `d8c0cab5-09dd-597f-9de7-7ca01aee2ec2`.
Revisión técnica `3ec6fa57-be3f-5433-8557-8c12c3eea740`.
Solicitud idempotente `7d4cacb1-3d85-53f6-9828-8a7b1e0164c5`.
Intento `4cd0cf3f-37df-4490-9f26-eb2763f3b4e6`.
Run `79f39931-ac71-4bc1-a317-149a975d1f74`.

El ejecutor oficial controlled execute está desacoplado de la terminal mediante `docker compose exec -d`. No es una cola general ni un monitor externo. Ejecuta un solo intento, verifica su resultado y sale; no hay supervisor configurado para relanzarlo. La campaña no fue despausada. No repetir execute ni usar otra clave; si hay duda, consultar primero la solicitud persistida.

Consulta sin escrituras (intervalo recomendado: 2–5 minutos, no sondeo continuo):

```sh
docker compose exec -T -w /app/malaria_dl_local_project \
 -e PYTHONDONTWRITEBYTECODE=1 backend python -B - \
 < docs/audits/e9_3_intento_unico_2026-09-14/consultar.py
```

El JSON identifica sesión, estado, recursos, épocas persistidas, archivos registrados y eventos oficiales. CPU: calcular diferencia de cpu_ticks dividida por clock_ticks_per_second y tiempo entre observaciones; no interpretar RSS como memoria exclusiva.

Log operativo persistente dentro del volumen de artefactos:
`/app/var/artifacts/controlled_7d4cacb1-3d85-53f6-9828-8a7b1e0164c5.log`.
El shell de lanzamiento añade `CONTROLLED_CLI_EXIT` cuando termina el CLI; la salida del worker se conserva por separado en eventos oficiales. Los fallos del CLI no equivalen automáticamente a OOM. El código de lanzamiento se conserva en `lanzamiento.sh` como evidencia, no como recomendación de repetirlo.

Al terminar, consultar desde otra conexión, comprobar sesión verified, artefactos/linaje, salida e inexistencia de hijos. Si sigue active, no reanudar. Si falla, no reservar otro intento; conservar todo y diagnosticar. Si queda completed sin verified, no declarar éxito y no avanzar. Si el gate retiene evidencia de procesos incierta, no forzar liberación.

TEST, EVALUATE, EXPLAIN, ensembles y E9.4 siguen fuera de alcance. La continuación de la campaña necesita otra autorización. No se promete seguimiento automático fuera de la sesión: sólo permanece el ejecutor oficial con sus controles y persistencia.
