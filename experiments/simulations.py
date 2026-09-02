import json
import csv
import os
import numpy as np
from scipy import stats
from model.environment import Environment
from agents.person import EvacueeAgent

RESULTS_DIR = "resultados"
PLANOS_DIR = "planos"
N_AGENTS = 100
MAX_STEPS = 500
CONFIDENCE = 0.95
REL_ERROR_THRESHOLD = 0.05
MIN_REPLICAS = 30

os.makedirs(RESULTS_DIR, exist_ok=True)

def run_simulation(replica_id):
    env = Environment(PLANOS_DIR)
    agents = EvacueeAgent.generate_random_agents(N_AGENTS, env)

    timestep = 0
    while any(a.is_active() for a in agents) and timestep < MAX_STEPS:
        env.reset_occupancy()
        env.reset_waiting_lists()
        for agent in agents:
            agent.step()
        timestep += 1

    tiempo_escapes = [a.total_steps for a in agents if a.state == "escaped"]

    sim_result = {
        "replica": replica_id,
        "duracion_simulacion": timestep,
        "tiempo_escape_promedio": np.mean(tiempo_escapes) if tiempo_escapes else None,
    }

    agent_data = []
    for a in agents:
        agent_data.append({
            "replica": replica_id,
            "id": a.id,
            "tipo": a.tipo,
            "estado": a.state,
            "tiempo_total": a.total_steps,
            "espera_total": a.total_steps_waiting,
            "espera_salida": a.total_steps_waiting_exit,
            "espera_escaleras": a.total_steps_waiting_stairs,
            "pasos_panico": a.panico_steps,
            "puerta_salida": a.puerta_salida,
            "escaleras_usadas": a.escaleras_usadas,
            "historial_humo": a.historial_humo,
        })

    return sim_result, agent_data

def calcular_intervalo_confianza(valores):
    n = len(valores)
    media = np.mean(valores)
    sem = stats.sem(valores)
    intervalo = stats.t.interval(CONFIDENCE, n-1, loc=media, scale=sem)
    error_relativo = sem / media if media != 0 else float('inf')
    return media, intervalo, error_relativo

def main():
    replicas = 0
    resultados = []
    resultados_agentes = []

    while True:
        sim_result, agentes_result = run_simulation(replicas + 1)
        resultados.append(sim_result)
        resultados_agentes.extend(agentes_result)
        replicas += 1

        if replicas >= MIN_REPLICAS:
            tiempos_sim = [r["duracion_simulacion"] for r in resultados]

            media, intervalo, err_sim = calcular_intervalo_confianza(tiempos_sim)

            print(f"Replica {replicas}: Tiempo sim promedio = {media:.2f}, IC = {intervalo}, Error relativo = {err_sim:.4f}")

            if err_sim < REL_ERROR_THRESHOLD:
                break

    with open(os.path.join(RESULTS_DIR, "resultados_globales.json"), "w") as f:
        json.dump(resultados, f, indent=4)

    with open(os.path.join(RESULTS_DIR, "resultados_agentes.json"), "w") as f:
        json.dump(resultados_agentes, f, indent=4)

    print(f"Simulaciones completas: {replicas}")

if __name__ == "__main__":
    main()
