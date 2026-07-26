# PostgreSQL efímero

`docker-compose.test.yml` usa PostgreSQL 17, base/usuario `capstone_test`, puerto loopback 55433, red etiquetada, healthcheck y `tmpfs`. `down -v` elimina datos. Los scripts `test_db_{up,wait,bootstrap,reset,down,status}.sh` son no interactivos, fallan con código distinto de cero y se ejecutan desde la raíz.
