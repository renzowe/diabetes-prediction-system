def test_resultados_rechaza_sin_clave_de_acceso(client):
    r = client.get("/resultados/evaluaciones")
    assert r.status_code == 401


def test_resultados_rechaza_clave_incorrecta(client):
    r = client.get("/resultados/evaluaciones", headers={"X-API-Key": "clave-equivocada"})
    assert r.status_code == 401


def test_listar_evaluaciones_filtra_por_participante(client, payload_perfil_bajo, auth_headers):
    client.post("/predict", json={**payload_perfil_bajo, "participante_codigo": "TEST_FILTRO"})  # /predict es publico

    r = client.get("/resultados/evaluaciones?participante_codigo=TEST_FILTRO", headers=auth_headers)
    assert r.status_code == 200
    registros = r.json()
    assert len(registros) == 1
    assert registros[0]["participante_codigo"] == "TEST_FILTRO"


def test_exportar_evaluaciones_csv_tiene_las_columnas_esperadas(client, payload_perfil_bajo, auth_headers):
    client.post("/predict", json=payload_perfil_bajo)

    r = client.get("/resultados/evaluaciones/export", headers=auth_headers)
    assert r.status_code == 200
    assert r.headers["content-type"].startswith("text/csv")

    encabezado = r.text.splitlines()[0]
    for columna in ["probabilidad", "imc", "cintura_cm", "tiempo_prediccion_ms", "modelo_archivo"]:
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


def test_resumen_reporta_rendimiento_y_usabilidad(client, payload_perfil_bajo, auth_headers):
    client.post("/predict", json=payload_perfil_bajo)
    client.post("/sus", json={"participante_codigo": "TEST_RESUMEN", "respuestas": [5, 1, 5, 1, 5, 1, 5, 1, 5, 1]})

    r = client.get("/resultados/resumen", headers=auth_headers)
    assert r.status_code == 200
    data = r.json()
    assert data["evaluaciones"] >= 1
    assert data["tiempo_prediccion_ms"]["porcentaje_menor_a_2000_ms"] == 100.0
    assert data["encuestas_sus"] >= 1
    assert 0 <= data["puntaje_sus"]["media"] <= 100


def test_resumen_requiere_clave(client):
    assert client.get("/resultados/resumen").status_code == 401


def test_produccion_exige_una_clave_propia():
    import pytest

    from app.config import Settings, validar_configuracion

    postgres = "postgresql://usuario:clave@servidor/base"
    with pytest.raises(RuntimeError):
        validar_configuracion(Settings(DATABASE_URL=postgres, API_KEY="change-me-too"))
    validar_configuracion(Settings(DATABASE_URL=postgres, API_KEY="una-clave-propia"))
