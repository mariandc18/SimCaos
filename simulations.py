import json
import os
import numpy as np
import random
import matplotlib.pyplot as plt
from scipy import stats
from model.environment import Environment
from model.fire_spread import FireManager
from agents.person import EvacueeAgent

RESULTS_DIR = "resultados"
PLANOS_DIR = "planos"
N_AGENTS = 40
MAX_STEPS = 600
CONFIDENCE = 0.99
REL_ERROR_THRESHOLD = 0.01
MIN_REPLICAS = 3

os.makedirs(RESULTS_DIR, exist_ok=True)

def run_simulation(replica_id):
    random.seed(replica_id)
    np.random.seed(replica_id)

    env = Environment(PLANOS_DIR)
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

def calculate_confidence_interval(values):
    values = [v for v in values if v is not None]
    n = len(values)
    if n < 2 or np.std(values) == 0:
        return np.mean(values) if values else 0, (0, 0), 0.0

    mean_val = np.mean(values)
    sem = stats.sem(values)
    interval = stats.t.interval(CONFIDENCE, n-1, loc=mean_val, scale=sem)
    rel_error = sem / mean_val if mean_val != 0 else float('inf')
    return mean_val, interval, rel_error

def main():
    replicas = 0
    resultados = []
    resultados_agentes = []
    tiempos_simulacion = []

    while True:
        sim_result, agentes_result = run_simulation(replicas + 1)
        resultados.append(sim_result)
        resultados_agentes.extend(agentes_result)
        replicas += 1

        tiempos_simulacion.append(sim_result["duracion_simulacion"])

        if replicas >= MIN_REPLICAS:
            mean_val, interval, err_sim = calculate_confidence_interval(tiempos_simulacion)
            print(f"Replica {replicas}: tiempo prom simulacion = {mean_val:.2f}, CI = {interval}, Relative error = {err_sim:.4f}")

            if err_sim < REL_ERROR_THRESHOLD:
                break

    with open(os.path.join(RESULTS_DIR, "resultados_globales.json"), "w") as f:
        json.dump(resultados, f, indent=4)

    with open(os.path.join(RESULTS_DIR, "resultados_agentes.json"), "w") as f:
        json.dump(resultados_agentes, f, indent=4)

    print(f"Simulaciones completadas: {replicas}")

    plt.figure(figsize=(10, 6))
    plt.plot(range(1, replicas + 1), tiempos_simulacion, marker='o', linestyle='-')
    plt.xlabel("Numero de replicas")
    plt.ylabel("Duracion de la simulacion")
    plt.title("Convergencia de la duracion de la simulacion")
    plt.grid(True)
    plt.tight_layout()
    plt.savefig(os.path.join(RESULTS_DIR, "convergencia_simulacion.png"))
    plt.show()

if __name__ == "__main__":
    main()
