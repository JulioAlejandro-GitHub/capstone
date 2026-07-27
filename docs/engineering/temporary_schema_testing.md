# Pruebas con schemas temporales

Solo se usan cuando rollback no basta para aislar objetos DDL. El nombre se genera con
prefijo `capstone_test_`, se valida antes de citarlo como identificador, se configura con
`SET LOCAL search_path`, y se elimina en `finally`. No se copian datos ni se ejecutan las
migraciones históricas 001–029. `make test-schema-clean` lista residuos y solo elimina con
`CONFIRM_DROP_TEMPORARY_TEST_SCHEMAS=true`.
