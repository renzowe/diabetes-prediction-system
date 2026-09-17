def test_resultados_rechaza_sin_clave_de_acceso(client):
    r = client.get("/resultados/evaluaciones")
    assert r.status_code == 401


def test_resultados_rechaza_clave_incorrecta(client):
    r = client.get("/resultados/evaluaciones", headers={"X-API-Key": "clave-equivocada"})
    assert r.status_code == 401


def test_listar_evaluaciones_filtra_por_participante(client, payload_bajo_riesgo, auth_headers):
    payload = {**payload_bajo_riesgo, "participante_codigo": "TEST_FILTRO", "momento": "manual"}
    client.post("/predict", json=payload)  # /predict sigue siendo publico, sin clave

    r = client.get("/resultados/evaluaciones?participante_codigo=TEST_FILTRO", headers=auth_headers)
    assert r.status_code == 200
    registros = r.json()
    assert len(registros) == 1
    assert registros[0]["participante_codigo"] == "TEST_FILTRO"


def test_exportar_evaluaciones_csv_tiene_las_columnas_esperadas(client, payload_bajo_riesgo, auth_headers):
    client.post("/predict", json=payload_bajo_riesgo)

    r = client.get("/resultados/evaluaciones/export", headers=auth_headers)
    assert r.status_code == 200
    assert r.headers["content-type"].startswith("text/csv")

    encabezado = r.text.splitlines()[0]
    for columna in ["probabilidad", "prediccion", "hba1c", "glucosa", "tiempo_segundos"]:
        assert columna in encabezado


def test_exportar_sus_csv_tiene_las_columnas_esperadas(client, auth_headers):
    client.post("/sus", json={
        "participante_codigo": "TEST_EXPORT_SUS",
        "respuestas": [4, 2, 4, 2, 4, 2, 4, 2, 4, 2],
    })

    r = client.get("/resultados/sus/export", headers=auth_headers)
    assert r.status_code == 200
    encabezado = r.text.splitlines()[0]
    assert "puntaje_sus" in encabezado
    assert "participante_codigo" in encabezado