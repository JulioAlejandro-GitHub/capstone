# Configuración

Las credenciales E2E solo se aceptan mediante `CAPSTONE_E2E_USERNAME` y
`CAPSTONE_E2E_PASSWORD` privadas y nunca se documentan con valores.

`APP_ENV=development` es el único ambiente. La plantilla raíz `.env.example`
es única para API/ML y no contiene secretos ni una URL de base operativa;
`frontend/.env.example` sólo declara configuración pública de Vite.
`DATABASE_URL` y `JWT_SECRET` son obligatorios. `TEST_DATABASE_URL` se rechaza:
los tests usan la misma base con aislamiento obligatorio. Drops de base y de `public`
permanecen deshabilitados.

Passwords, tokens y URLs completas no se registran. CORS acepta orígenes HTTP(S) explícitos.
