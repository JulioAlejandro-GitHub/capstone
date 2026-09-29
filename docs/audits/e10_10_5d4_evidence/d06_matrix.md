# D-06 — matriz individual de equivalencia en PostgreSQL 17.9

Diagnóstico ejecutado sobre legacy aislado y Ruta A D-03. La nueva Ruta A D.4 conserva exactamente estas definiciones, árboles canónicos, objetos resueltos y dependencias, acreditado en `route_a/contract_continuity.json`. No se modificó ninguna de las cuatro restricciones.

| Restricción | Fixtures por catálogo | Equivalencia | Decisión aplicada |
|---|---:|---|---|
| campaign_controlled_requests_reason_check | 10 | Demostrada | Formato de llamada del mismo `pg_catalog.btrim(text)`. |
| ck_cell_prediction_label_index | 1920 | Demostrada | Asociatividad ordenada de AND/OR en lógica SQL de tres valores. |
| ck_smear_summary_fraction | 200 | Demostrada | Asociatividad ordenada de AND/OR en lógica SQL de tres valores. |
| ck_smear_summary_probabilities | 1080 | Demostrada | Asociatividad ordenada de AND/OR en lógica SQL de tres valores. |

La prueba compara el predicado y el INSERT efectivo bajo CHECK: TRUE y UNKNOWN permiten insertar; FALSE produce SQLSTATE 23514. Los NULL de los fixtures aíslan CHECK de las restricciones NOT NULL de la tabla real. No se eliminó ninguna restricción real. La matriz incluye valores válidos, inválidos, límites, combinaciones NULL y tolerancia 1e-9; los 27 triples TRUE/FALSE/NULL verifican adicionalmente la asociatividad AND/OR en el nuevo servidor.

La equivalencia se fundamenta en árboles nativos completos y bindings, además de los ejemplos. Se eliminan solo ubicaciones de texto; para funcid 885 se equiparan funcformat 0/3 tras exigir el mismo objeto y propiedades; se aplanan AND/OR del mismo tipo conservando el orden. Operadores, casts, collation, constantes, atributos y restantes campos siguen siendo exactos. No hay simplificación algebraica ni permutación de operandos.

## campaign_controlled_requests_reason_check

**Legacy**
```sql
CHECK ((length(TRIM(BOTH FROM reason)) > 0))
```

**Ruta A (D-03 y D.4)**
```sql
CHECK ((length(btrim(reason)) > 0))
```

**Dependencias nativas idénticas**
```json
[
  {
    "deptype": "a",
    "catalog": "pg_class",
    "object": "column reason of table campaign_controlled_requests"
  },
  {
    "deptype": "n",
    "catalog": "pg_class",
    "object": "column reason of table campaign_controlled_requests"
  }
]
```

**Objetos resueltos idénticos**
```json
{
  "funcid": [
    {
      "oid": 885,
      "object": "btrim(text)"
    },
    {
      "oid": 1317,
      "object": "length(text)"
    }
  ],
  "opno": [
    {
      "oid": 521,
      "object": ">(integer,integer)"
    }
  ],
  "opfuncid": [
    {
      "oid": 147,
      "object": "int4gt(integer,integer)"
    }
  ],
  "consttype": [
    {
      "oid": 23,
      "object": "integer"
    }
  ],
  "vartype": [
    {
      "oid": 25,
      "object": "text"
    }
  ],
  "resulttype": [],
  "funcresulttype": [
    {
      "oid": 23,
      "object": "integer"
    },
    {
      "oid": 25,
      "object": "text"
    }
  ]
}
```

**Resultado:** 10 fixtures por catálogo, sin divergencias de predicado ni aceptación CHECK. Equivalencia demostrada. Hash del árbol canónico: `de4f8a950942dbc4b95520a40938c47673764712c2068209640ebb3dc2037236`. Los valores de entrada y cada resultado se conservan en `d06_native_and_tests.json`.

## ck_cell_prediction_label_index

**Legacy**
```sql
CHECK ((((prediction_status)::text <> 'completed'::text) OR (((predicted_class_index = 1) AND ((predicted_label)::text = 'parasitized'::text) AND (probability_parasitized >= threshold_used)) OR ((predicted_class_index = 0) AND ((predicted_label)::text = 'uninfected'::text) AND (probability_parasitized < threshold_used)))))
```

**Ruta A (D-03 y D.4)**
```sql
CHECK ((((prediction_status)::text <> 'completed'::text) OR ((predicted_class_index = 1) AND ((predicted_label)::text = 'parasitized'::text) AND (probability_parasitized >= threshold_used)) OR ((predicted_class_index = 0) AND ((predicted_label)::text = 'uninfected'::text) AND (probability_parasitized < threshold_used))))
```

**Dependencias nativas idénticas**
```json
[
  {
    "deptype": "a",
    "catalog": "pg_class",
    "object": "column predicted_class_index of table cell_predictions"
  },
  {
    "deptype": "a",
    "catalog": "pg_class",
    "object": "column predicted_label of table cell_predictions"
  },
  {
    "deptype": "a",
    "catalog": "pg_class",
    "object": "column prediction_status of table cell_predictions"
  },
  {
    "deptype": "a",
    "catalog": "pg_class",
    "object": "column probability_parasitized of table cell_predictions"
  },
  {
    "deptype": "a",
    "catalog": "pg_class",
    "object": "column threshold_used of table cell_predictions"
  },
  {
    "deptype": "n",
    "catalog": "pg_class",
    "object": "column predicted_class_index of table cell_predictions"
  },
  {
    "deptype": "n",
    "catalog": "pg_class",
    "object": "column predicted_label of table cell_predictions"
  },
  {
    "deptype": "n",
    "catalog": "pg_class",
    "object": "column prediction_status of table cell_predictions"
  },
  {
    "deptype": "n",
    "catalog": "pg_class",
    "object": "column probability_parasitized of table cell_predictions"
  },
  {
    "deptype": "n",
    "catalog": "pg_class",
    "object": "column threshold_used of table cell_predictions"
  }
]
```

**Objetos resueltos idénticos**
```json
{
  "funcid": [],
  "opno": [
    {
      "oid": 98,
      "object": "=(text,text)"
    },
    {
      "oid": 531,
      "object": "<>(text,text)"
    },
    {
      "oid": 532,
      "object": "=(smallint,integer)"
    },
    {
      "oid": 672,
      "object": "<(double precision,double precision)"
    },
    {
      "oid": 675,
      "object": ">=(double precision,double precision)"
    }
  ],
  "opfuncid": [
    {
      "oid": 67,
      "object": "texteq(text,text)"
    },
    {
      "oid": 157,
      "object": "textne(text,text)"
    },
    {
      "oid": 158,
      "object": "int24eq(smallint,integer)"
    },
    {
      "oid": 295,
      "object": "float8lt(double precision,double precision)"
    },
    {
      "oid": 298,
      "object": "float8ge(double precision,double precision)"
    }
  ],
  "consttype": [
    {
      "oid": 23,
      "object": "integer"
    },
    {
      "oid": 25,
      "object": "text"
    }
  ],
  "vartype": [
    {
      "oid": 21,
      "object": "smallint"
    },
    {
      "oid": 701,
      "object": "double precision"
    },
    {
      "oid": 1043,
      "object": "character varying"
    }
  ],
  "resulttype": [
    {
      "oid": 25,
      "object": "text"
    }
  ],
  "funcresulttype": []
}
```

**Resultado:** 1920 fixtures por catálogo, sin divergencias de predicado ni aceptación CHECK. Equivalencia demostrada. Hash del árbol canónico: `83f4eecb2c93d45397e705841d46915da5ded448611bb1eba5591da43fb2de91`. Los valores de entrada y cada resultado se conservan en `d06_native_and_tests.json`.

## ck_smear_summary_fraction

**Legacy**
```sql
CHECK ((((classified_cell_count = 0) AND (parasitized_candidate_fraction IS NULL)) OR ((classified_cell_count > 0) AND ((parasitized_candidate_fraction >= (0)::double precision) AND (parasitized_candidate_fraction <= (1)::double precision)) AND (abs((parasitized_candidate_fraction - ((parasitized_candidate_count)::double precision / (classified_cell_count)::double precision))) <= (0.000000001)::double precision))))
```

**Ruta A (D-03 y D.4)**
```sql
CHECK ((((classified_cell_count = 0) AND (parasitized_candidate_fraction IS NULL)) OR ((classified_cell_count > 0) AND (parasitized_candidate_fraction >= (0)::double precision) AND (parasitized_candidate_fraction <= (1)::double precision) AND (abs((parasitized_candidate_fraction - ((parasitized_candidate_count)::double precision / (classified_cell_count)::double precision))) <= (0.000000001)::double precision))))
```

**Dependencias nativas idénticas**
```json
[
  {
    "deptype": "a",
    "catalog": "pg_class",
    "object": "column classified_cell_count of table smear_analysis_summaries"
  },
  {
    "deptype": "a",
    "catalog": "pg_class",
    "object": "column parasitized_candidate_count of table smear_analysis_summaries"
  },
  {
    "deptype": "a",
    "catalog": "pg_class",
    "object": "column parasitized_candidate_fraction of table smear_analysis_summaries"
  },
  {
    "deptype": "n",
    "catalog": "pg_class",
    "object": "column classified_cell_count of table smear_analysis_summaries"
  },
  {
    "deptype": "n",
    "catalog": "pg_class",
    "object": "column parasitized_candidate_count of table smear_analysis_summaries"
  },
  {
    "deptype": "n",
    "catalog": "pg_class",
    "object": "column parasitized_candidate_fraction of table smear_analysis_summaries"
  }
]
```

**Objetos resueltos idénticos**
```json
{
  "funcid": [
    {
      "oid": 316,
      "object": "float8(integer)"
    },
    {
      "oid": 1395,
      "object": "abs(double precision)"
    },
    {
      "oid": 1746,
      "object": "float8(numeric)"
    }
  ],
  "opno": [
    {
      "oid": 96,
      "object": "=(integer,integer)"
    },
    {
      "oid": 521,
      "object": ">(integer,integer)"
    },
    {
      "oid": 592,
      "object": "-(double precision,double precision)"
    },
    {
      "oid": 593,
      "object": "/(double precision,double precision)"
    },
    {
      "oid": 673,
      "object": "<=(double precision,double precision)"
    },
    {
      "oid": 675,
      "object": ">=(double precision,double precision)"
    }
  ],
  "opfuncid": [
    {
      "oid": 65,
      "object": "int4eq(integer,integer)"
    },
    {
      "oid": 147,
      "object": "int4gt(integer,integer)"
    },
    {
      "oid": 217,
      "object": "float8div(double precision,double precision)"
    },
    {
      "oid": 219,
      "object": "float8mi(double precision,double precision)"
    },
    {
      "oid": 296,
      "object": "float8le(double precision,double precision)"
    },
    {
      "oid": 298,
      "object": "float8ge(double precision,double precision)"
    }
  ],
  "consttype": [
    {
      "oid": 23,
      "object": "integer"
    },
    {
      "oid": 1700,
      "object": "numeric"
    }
  ],
  "vartype": [
    {
      "oid": 23,
      "object": "integer"
    },
    {
      "oid": 701,
      "object": "double precision"
    }
  ],
  "resulttype": [],
  "funcresulttype": [
    {
      "oid": 701,
      "object": "double precision"
    }
  ]
}
```

**Resultado:** 200 fixtures por catálogo, sin divergencias de predicado ni aceptación CHECK. Equivalencia demostrada. Hash del árbol canónico: `362b5fe0d8837a52953fb2cb1400bc405f0066d0e987722bf731e59c8ca68dbd`. Los valores de entrada y cada resultado se conservan en `d06_native_and_tests.json`.

## ck_smear_summary_probabilities

**Legacy**
```sql
CHECK ((((classified_cell_count = 0) AND (maximum_probability_parasitized IS NULL) AND (mean_probability_parasitized IS NULL) AND (median_probability_parasitized IS NULL)) OR ((classified_cell_count > 0) AND ((maximum_probability_parasitized >= (0)::double precision) AND (maximum_probability_parasitized <= (1)::double precision)) AND ((mean_probability_parasitized >= (0)::double precision) AND (mean_probability_parasitized <= (1)::double precision)) AND ((median_probability_parasitized >= (0)::double precision) AND (median_probability_parasitized <= (1)::double precision)))))
```

**Ruta A (D-03 y D.4)**
```sql
CHECK ((((classified_cell_count = 0) AND (maximum_probability_parasitized IS NULL) AND (mean_probability_parasitized IS NULL) AND (median_probability_parasitized IS NULL)) OR ((classified_cell_count > 0) AND (maximum_probability_parasitized >= (0)::double precision) AND (maximum_probability_parasitized <= (1)::double precision) AND (mean_probability_parasitized >= (0)::double precision) AND (mean_probability_parasitized <= (1)::double precision) AND (median_probability_parasitized >= (0)::double precision) AND (median_probability_parasitized <= (1)::double precision))))
```

**Dependencias nativas idénticas**
```json
[
  {
    "deptype": "a",
    "catalog": "pg_class",
    "object": "column classified_cell_count of table smear_analysis_summaries"
  },
  {
    "deptype": "a",
    "catalog": "pg_class",
    "object": "column maximum_probability_parasitized of table smear_analysis_summaries"
  },
  {
    "deptype": "a",
    "catalog": "pg_class",
    "object": "column mean_probability_parasitized of table smear_analysis_summaries"
  },
  {
    "deptype": "a",
    "catalog": "pg_class",
    "object": "column median_probability_parasitized of table smear_analysis_summaries"
  },
  {
    "deptype": "n",
    "catalog": "pg_class",
    "object": "column classified_cell_count of table smear_analysis_summaries"
  },
  {
    "deptype": "n",
    "catalog": "pg_class",
    "object": "column maximum_probability_parasitized of table smear_analysis_summaries"
  },
  {
    "deptype": "n",
    "catalog": "pg_class",
    "object": "column mean_probability_parasitized of table smear_analysis_summaries"
  },
  {
    "deptype": "n",
    "catalog": "pg_class",
    "object": "column median_probability_parasitized of table smear_analysis_summaries"
  }
]
```

**Objetos resueltos idénticos**
```json
{
  "funcid": [
    {
      "oid": 316,
      "object": "float8(integer)"
    }
  ],
  "opno": [
    {
      "oid": 96,
      "object": "=(integer,integer)"
    },
    {
      "oid": 521,
      "object": ">(integer,integer)"
    },
    {
      "oid": 673,
      "object": "<=(double precision,double precision)"
    },
    {
      "oid": 675,
      "object": ">=(double precision,double precision)"
    }
  ],
  "opfuncid": [
    {
      "oid": 65,
      "object": "int4eq(integer,integer)"
    },
    {
      "oid": 147,
      "object": "int4gt(integer,integer)"
    },
    {
      "oid": 296,
      "object": "float8le(double precision,double precision)"
    },
    {
      "oid": 298,
      "object": "float8ge(double precision,double precision)"
    }
  ],
  "consttype": [
    {
      "oid": 23,
      "object": "integer"
    }
  ],
  "vartype": [
    {
      "oid": 23,
      "object": "integer"
    },
    {
      "oid": 701,
      "object": "double precision"
    }
  ],
  "resulttype": [],
  "funcresulttype": [
    {
      "oid": 701,
      "object": "double precision"
    }
  ]
}
```

**Resultado:** 1080 fixtures por catálogo, sin divergencias de predicado ni aceptación CHECK. Equivalencia demostrada. Hash del árbol canónico: `0a45118f7255a593bd7416d063e1730d2c23f0a55cc5096ea7fa06948b0ca8dc`. Los valores de entrada y cada resultado se conservan en `d06_native_and_tests.json`.
