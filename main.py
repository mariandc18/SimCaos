from model.environment import Environment
from model.fire_spread import FireManager
from agents.person import EvacueeAgent

env = Environment("planos/")
fire = FireManager(env)

for exit_pos in env.get_all_exits():
    env.set_exit_capacity(*exit_pos, cap=2)  

for stairs_pos in env.get_all_stairs():
    env.set_stairs_capacity(*stairs_pos, cap=2)  

agents = EvacueeAgent.generate_random_agents(40, env)
fire.ignite(1, 2, 1)

for step in range(20):
    print(f"\n--- Timestep {step} ---")
    
    env.reset_occupancy() 
    env.reset_waiting_lists()
    fire.step()                  

    for agent in agents:
        agent.step()
        pos = agent.get_position()
        estado = agent.state
        print(f"Agente {agent.id}: {pos} - {estado}")
        
    print("\n Agentes esperando en salidas:")
    for pos, ids in env.waiting_exit.items():
        if ids:
            print(f"{len(ids)}. Agentes: {ids}")

    print("\n Agentes esperando en escaleras:")
    for pos, ids in env.waiting_stairs.items():
        if ids:
            print(f"{len(ids)}. Agentes: {ids}")


