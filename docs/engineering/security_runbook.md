# Runbook de seguridad

Rote `JWT_SECRET` generando al menos 32 bytes aleatorios, actualice el secret del entorno y reinicie API; los tokens anteriores dejan de ser válidos. Ante intento de DB no autorizada, preserve el error de la guarda, verifique host/puerto/nombre sin copiar credenciales y no fuerce el reset. Deshabilite el usuario comprometido y rote su password. Nunca incluya `.env` en tickets o logs.
