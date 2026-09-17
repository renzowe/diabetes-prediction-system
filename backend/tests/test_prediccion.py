def test_estado_ok(client):
    r = client.get("/")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


def test_predict_bajo_riesgo(client, payload_bajo_riesgo):
    r = client.post("/predict", json=payload_bajo_riesgo)
    assert r.status_code == 200
    data = r.json()
    assert data["nivel_riesgo"] == "bajo"
    assert data["probabilidad"] < 0.30
    assert data["prediccion"] == 0


def test_predict_alto_riesgo(client, payload_alto_riesgo):
    r = client.post("/predict", json=payload_alto_riesgo)
    assert r.status_code == 200
    data = r.json()
    assert data["nivel_riesgo"] == "alto"
    assert data["probabilidad"] > 0.60
    assert data["prediccion"] == 1


def test_predict_rechaza_edad_fuera_de_rango(client, payload_bajo_riesgo):
    payload = {**payload_bajo_riesgo, "edad": 20}  # fuera de 30-64
    r = client.post("/predict", json=payload)
    assert r.status_code == 422


def test_predict_rechaza_imc_fuera_de_rango(client, payload_bajo_riesgo):
    payload = {**payload_bajo_riesgo, "imc": 5}  # fuera de 10-70
    r = client.post("/predict", json=payload)
    assert r.status_code == 422


def test_predict_rechaza_campo_faltante(client, payload_bajo_riesgo):
    payload = payload_bajo_riesgo.copy()
    del payload["glucosa"]
    r = client.post("/predict", json=payload)
    assert r.status_code == 422


def test_predict_guarda_metadatos_de_pretest_postest(client, payload_bajo_riesgo, auth_headers):
    payload = {
        **payload_bajo_riesgo,
        "momento": "sistema",
        "tiempo_segundos": 15.2,
        "participante_codigo": "TEST_META",
    }
    r = client.post("/predict", json=payload)
    assert r.status_code == 200

    r = client.get("/resultados/evaluaciones?participante_codigo=TEST_META", headers=auth_headers)
    registros = r.json()
    assert len(registros) == 1
    assert registros[0]["momento"] == "sistema"
    assert registros[0]["tiempo_segundos"] == 15.2