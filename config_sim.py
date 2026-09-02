import os
import csv
import json
import numpy as np
import random
from scipy import stats
from model.environment import Environment
from model.fire_spread import FireManager
from agents.person import EvacueeAgent


PLANOS_BASE_DIR = "planos"
CONFIGS_DIR = "planos_variantes"
RESULTADOS_DIR = "resultados_comparativos"
N_CONFIGS = 35
PUERTAS_EXTRA_RANGO = (1, 4)
ESCALERAS_EXTRA_RANGO = (1, 5)
N_AGENTS = 40
MAX_STEPS = 600
CONFIDENCE = 0.95
REL_ERROR_THRESHOLD = 0.01
MIN_REPLICAS = 3

os.makedirs(CONFIGS_DIR, exist_ok=True)
os.makedirs(RESULTADOS_DIR, exist_ok=True)

def cargar_plano(csv_path):
    with open(csv_path, newline='') as f:
        return [[int(cell) for cell in row] for row in csv.reader(f)]

def guardar_plano(matriz, path):
    with open(path, "w", newline='') as f:
        csv.writer(f).writerows(matriz)

def calcular_ic(valores):
    valores = [v for v in valores if v is not None]
    n = len(valores)
    if n < 2 or np.std(valores) == 0:
        return np.mean(valores), (0, 0), 0.0
    media = np.mean(valores)
    sem = stats.sem(valores)
    intervalo = stats.t.interval(CONFIDENCE, n - 1, loc=media, scale=sem)
    error_relativo = sem / media if media != 0 else float('inf')
    return media, intervalo, error_relativo

def generar_configuracion(id_config):
    carpeta = os.path.join(CONFIGS_DIR, f"config_{id_config}")
    os.makedirs(carpeta, exist_ok=True)

    piso_files = sorted([f for f in os.listdir(PLANOS_BASE_DIR) if f.endswith(".csv")])
    matrices = []
    puertas_por_piso = []

    for piso_file in piso_files:
        matriz = cargar_plano(os.path.join(PLANOS_BASE_DIR, piso_file))
        filas, cols = len(matriz), len(matriz[0])
        n_puertas = random.randint(*PUERTAS_EXTRA_RANGO)
        puertas = 0
        while puertas < n_puertas:
            x, y = random.randint(0, filas - 1), random.randint(0, cols - 1)
            if matriz[x][y] == Environment.FREE:
                matriz[x][y] = Environment.EXIT
                puertas += 1
        puertas_por_piso.append(puertas)
        matrices.append(matriz)

    escaleras_totales = 0
    n_esc = random.randint(*ESCALERAS_EXTRA_RANGO)
    for _ in range(n_esc):
        piso_z = random.randint(0, len(matrices) - 2)
        filas, cols = len(matrices[piso_z]), len(matrices[piso_z][0])
        intentos = 0
        while intentos < 20:
            x, y = random.randint(0, filas - 1), random.randint(0, cols - 1)
            if matrices[piso_z][x][y] == Environment.FREE and matrices[piso_z + 1][x][y] == Environment.FREE:
                matrices[piso_z][x][y] = Environment.STAIRS
                matrices[piso_z + 1][x][y] = Environment.STAIRS
                escaleras_totales += 1
                break
            intentos += 1

    for i, matriz in enumerate(matrices):
        guardar_plano(matriz, os.path.join(carpeta, f"piso_{i}.csv"))

    return carpeta, {
        "puertas_por_piso": puertas_por_piso,
        "escaleras_totales": escaleras_totales
    }

def simular_con_replicas(planos_path):
    replicas = 0
    duraciones = []
    escapados_total = 0
    muertos_total = 0
    tiempos_escapes = []

    while True:
        env = Environment(planos_path)
        env.reset_smoke()
        env.reset_fire()
        fire = FireManager(env)
        fire.ignite(3, 2, 1)

        agents = EvacueeAgent.generate_random_agents(N_AGENTS, env)
        timestep = 0
        while any(a.is_active() for a in agents) and timestep < MAX_STEPS:
            env.reset_occupancy()
            env.reset_waiting_lists()
            env.reset_occupancy_map()
            fire.step()
            for a in agents:
                a.step()
            timestep += 1

        escapados = [a for a in agents if a.state == "escaped"]
        muertos = [a for a in agents if a.state == "dead"]
        escapados_total += len(escapados)
        muertos_total += len(muertos)
        tiempos_escapes.extend([a.total_steps for a in escapados])
        duraciones.append(timestep)
        replicas += 1

        if replicas >= MIN_REPLICAS:
            media_dur, ic_dur, err_rel = calcular_ic(duraciones)
            if err_rel < REL_ERROR_THRESHOLD:
                break

    return {
        "replicas": replicas,
        "prom_duracion": media_dur,
        "ic_duracion": ic_dur,
        "n_escapados": escapados_total,
        "n_muertos": muertos_total,
        "prom_t_escapes": np.mean(tiempos_escapes) if tiempos_escapes else None
    }

def main():
    resultados = []
    for i in range(N_CONFIGS):
        print(f"Configuración {i+1}/{N_CONFIGS}")
        ruta_config, info_config = generar_configuracion(i)
        resultado = simular_con_replicas(ruta_config)
        resultado["config_id"] = i
        resultado["config_path"] = ruta_config
        resultado["info_config"] = info_config
        resultados.append(resultado)

    with open(os.path.join(RESULTADOS_DIR, "comparacion_configuraciones.json"), "w") as f:
        json.dump(resultados, f, indent=4)

    print(f"\nSimulación terminada. Resultados guardados en comparacion_configuraciones.json")

if __name__ == "__main__":
    main()

