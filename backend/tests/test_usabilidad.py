def test_sus_puntaje_neutral_es_50(client):
    # Con todas las respuestas en el punto medio (3), la formula SUS
    # siempre da exactamente 50 puntos, sin importar el orden de las preguntas.
    # Segun el umbral definido (>=51 = Aceptable), 50 exacto cae como 'Deficiente'.
    r = client.post("/sus", json={
        "participante_codigo": "TEST_SUS_NEUTRAL",
        "respuestas": [3, 3, 3, 3, 3, 3, 3, 3, 3, 3],
    })
    assert r.status_code == 200
    data = r.json()
    assert data["puntaje_sus"] == 50.0
    assert data["interpretacion"] == "Deficiente"


def test_sus_puntaje_maximo_es_100(client):
    # Impares (1,3,5,7,9) en 5 y pares (2,4,6,8,10) en 1 = puntaje maximo posible
    r = client.post("/sus", json={
        "participante_codigo": "TEST_SUS_MAX",
        "respuestas": [5, 1, 5, 1, 5, 1, 5, 1, 5, 1],
    })
    assert r.status_code == 200
    data = r.json()
    assert data["puntaje_sus"] == 100.0
    assert data["interpretacion"] == "Excelente"


def test_sus_rechaza_respuesta_fuera_de_rango(client):
    r = client.post("/sus", json={
        "participante_codigo": "TEST_SUS_INVALIDO",
        "respuestas": [6, 1, 5, 1, 5, 1, 5, 1, 5, 1],  # 6 no es valido (1-5)
    })
    assert r.status_code == 422


def test_sus_rechaza_menos_de_10_respuestas(client):
    r = client.post("/sus", json={
        "participante_codigo": "TEST_SUS_INCOMPLETO",
        "respuestas": [5, 1, 5, 1, 5],
    })
    assert r.status_code == 422
