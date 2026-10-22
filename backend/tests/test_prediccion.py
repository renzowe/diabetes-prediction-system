import json
from pathlib import Path

import joblib
import numpy as np
import pandas as pd

RAIZ = Path(__file__).resolve().parents[2]


def test_estado_informa_el_modelo_cargado(client):
    r = client.get("/")
    assert r.status_code == 200
    data = r.json()
    assert data["status"] == "ok"
    assert data["modelo"]["archivo"] == "web_regresion_logistica.joblib"


def test_predict_devuelve_probabilidad_factores_y_mensaje(client, payload_perfil_bajo):
    r = client.post("/predict", json=payload_perfil_bajo)
    assert r.status_code == 200
    data = r.json()
    assert 0 < data["probabilidad"] < 1
    assert data["prevalencia_referencia"] == round(562 / 8909, 4)
    assert data["imc"] == round(55 / 1.6**2, 2)
    assert "No es un diagnóstico" in data["mensaje"]
    assert "No son consejos de salud ni efectos causales" in data["nota_factores"]
    assert {f["efecto"] for f in data["factores"]} <= {"aumenta", "disminuye"}
    assert "nivel_riesgo" not in data  # sin categorias de riesgo (plan de tesis, 4.6.1)


def test_solo_se_muestran_edad_sexo_composicion_corporal_e_hipertension(client, payload_perfil_alto):
    factores = client.post("/predict", json=payload_perfil_alto).json()["factores"]
    assert {f["factor"] for f in factores} == {"Edad", "Sexo", "Composición corporal", "Hipertensión arterial"}
    contribuciones = [abs(f["contribucion"]) for f in factores]
    assert contribuciones == sorted(contribuciones, reverse=True)


def test_los_factores_muestran_el_valor_de_la_persona(client, payload_perfil_alto):
    valores = {f["factor"]: f["valor"] for f in client.post("/predict", json=payload_perfil_alto).json()["factores"]}
    assert valores["Edad"] == "66 años"
    assert valores["Sexo"] == "Hombre"
    assert valores["Hipertensión arterial"] == "Con diagnóstico médico"
    assert valores["Composición corporal"] == "IMC 33.8 · perímetro abdominal 115 cm"


def test_perfil_con_mas_factores_de_riesgo_tiene_mayor_probabilidad(client, payload_perfil_bajo, payload_perfil_alto):
    bajo = client.post("/predict", json=payload_perfil_bajo).json()["probabilidad"]
    alto = client.post("/predict", json=payload_perfil_alto).json()["probabilidad"]
    assert alto > bajo


def test_api_reproduce_exactamente_el_modelo_congelado(client, payload_perfil_alto):
    """La probabilidad de la API debe ser la misma que da el modelo de notebooks/03."""
    directorio = RAIZ / "models" / "v2"
    artefacto = joblib.load(directorio / json.loads((directorio / "seleccion.json").read_text())["web"])
    p = payload_perfil_alto
    fila = pd.DataFrame([{
        "edad": p["edad"], "hombre": 1.0, "imc": p["peso_kg"] / (p["talla_cm"] / 100) ** 2,
        "cintura": p["cintura_cm"], "hta": 1.0, "tabaco": 1.0, "alcohol": 0.0,
        "frutas_dias": p["dias_frutas"], "verduras_dias": p["dias_verduras"],
    }])[artefacto["predictores"]]
    esperada = artefacto["modelo"].predict_proba(fila)[0, 1]

    obtenida = client.post("/predict", json=p).json()["probabilidad"]
    assert abs(obtenida - esperada) < 1e-3  # la API redondea a 4 decimales; el IMC, a 2


def test_contribuciones_explican_la_probabilidad(client, payload_perfil_alto):
    """En el modelo lineal, intercepto + suma de todas las contribuciones (incluidas las que no se
    muestran) = log-odds de la probabilidad."""
    from app.schemas.diabetes import EvaluacionEntrada

    modelo = client.app.state.modelo
    resultado = modelo.predecir(EvaluacionEntrada(**payload_perfil_alto))
    assert set(resultado.contribuciones) == {"edad", "sexo", "composicion_corporal", "hipertension",
                                             "tabaco", "alcohol", "frutas", "verduras"}
    log_odds = modelo.intercepto + sum(resultado.contribuciones.values())
    assert abs(1 / (1 + np.exp(-log_odds)) - resultado.probabilidad) < 1e-9


def test_predict_rechaza_edad_fuera_del_rango_del_modelo(client, payload_perfil_bajo):
    for edad in (29, 70):
        r = client.post("/predict", json={**payload_perfil_bajo, "edad": edad})
        assert r.status_code == 422


def test_predict_rechaza_imc_no_plausible(client, payload_perfil_bajo):
    r = client.post("/predict", json={**payload_perfil_bajo, "peso_kg": 200, "talla_cm": 125})  # IMC = 128
    assert r.status_code == 422


def test_predict_rechaza_dias_fuera_de_rango(client, payload_perfil_bajo):
    r = client.post("/predict", json={**payload_perfil_bajo, "dias_frutas": 8})
    assert r.status_code == 422


def test_predict_rechaza_campo_faltante(client, payload_perfil_bajo):
    payload = payload_perfil_bajo.copy()
    del payload["cintura_cm"]
    assert client.post("/predict", json=payload).status_code == 422


def test_predict_guarda_la_evaluacion_con_su_tiempo(client, payload_perfil_bajo, auth_headers):
    client.post("/predict", json={**payload_perfil_bajo, "participante_codigo": "TEST_GUARDA"})
    registros = client.get("/resultados/evaluaciones?participante_codigo=TEST_GUARDA", headers=auth_headers).json()
    assert len(registros) == 1
    assert registros[0]["modelo_archivo"] == "web_regresion_logistica.joblib"
    assert 0 < registros[0]["tiempo_prediccion_ms"] < 2000
