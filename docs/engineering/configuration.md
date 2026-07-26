# Configuración

`APP_ENV=local|test|demo` selecciona la política. Consulte los tres `.env.*.example`; no se versionan `.env`. Demo exige JWT de al menos 32 caracteres, auth habilitada y paths absolutos. Test exige URL explícita. Local usa valores simples controlados, nunca `malaria_experiments`.

Variables de API, DB, auth, storage, observabilidad y futuro worker están inventariadas en `.env.example`. Las variables worker son sólo contrato: no existe worker científico. CORS acepta únicamente orígenes HTTP(S) explícitos. Passwords, tokens y URLs completas se sanitizan.
