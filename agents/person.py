import random
from collections import deque

TIPOS_DE_AGENTE = {
    "niño": {"delay": 1, "mode_probability": {"follow": 0.7, "solo": 0.3}},
    "adulto": {"delay": 1},
    "anciano": {"delay": 3},
}

class EvacueeAgent:
    def __init__(self, id, x, y, z, env, tipo="adulto", mode="solo", adulto_referencia=None):
        self.id = id
        self.x = x
        self.y = y
        self.z = z
        self.env = env
        self.tipo = tipo
        self.state = "alive"
        self.mode = mode
        self.adulto_referencia = adulto_referencia
        self.step_delay = TIPOS_DE_AGENTE.get(tipo, {}).get("delay", 1)
        self.steps_waited = 0
        self.historial_posiciones = []

        # Estado emocional
        self.estado_panico = False
        self.turnos_en_panico = 0
        self.reaccion_tardia = random.randint(0, 4) if self.tipo in ["adulto", "anciano"] and random.random() < 0.1 else 0
        
        # estadisticas del agente
        self.total_steps = 0
        self.total_steps_waiting = 0
        self.total_steps_waiting_exit = 0
        self.total_steps_waiting_stairs = 0
        self.panico_steps = 0
        self.historial_humo = []
        self.puerta_salida = None        
        self.escaleras_usadas = []       
        

    def get_position(self):
        return (self.x, self.y, self.z)

    def is_active(self):
        return self.state == "alive"

    def step(self):
        if not self.is_active():
            return
        
        self.total_steps += 1

        if self.reaccion_tardia > 0:
            self.reaccion_tardia -= 1
            return  # Aún no reacciona por shock inicial

        self.steps_waited += 1
        if self.steps_waited < self.step_delay:
            return
        self.steps_waited = 0
        
        # Registrar nivel de humo actual
        nivel_humo = self.env.get_smoke_category(self.x, self.y, self.z)
        self.historial_humo.append(nivel_humo)

        if self.env.is_on_fire(self.x, self.y, self.z):
            self.state = "dead"
            return

        self.historial_posiciones.append(self.get_position())

        if self.env.is_exit(self.x, self.y, self.z):
            self.state = "escaped"
            return

        # Posible entrada en pánico (solo adultos y ancianos)
        if self.tipo in ["adulto", "anciano"] and not self.estado_panico and random.random() < 0.01:
            self.estado_panico = True
            self.turnos_en_panico = random.randint(2, 4)
            print(f"Agente {self.id} ({self.tipo}) entra en pánico por {self.turnos_en_panico} pasos")

        # Comportamiento de pánico (adultos y ancianos)
        if self.estado_panico:
            if self.turnos_en_panico > 0:
                self.turnos_en_panico -= 1
                reaccion = random.choice(["paralisis", "desorientado", "acelerado"])
                
                if reaccion == "paralisis":
                    print(f"Agente {self.id} ({self.tipo}) paralizado por pánico")
                    return

                elif reaccion == "desorientado":
                    vecinos = self.env.get_neighbors(self.x, self.y, self.z, include_vertical=True)
                    seguros = [v for v in vecinos if not self.env.is_on_fire(*v)]
                    if seguros:
                        nuevo_pos = random.choice(seguros)
                        print(f"Agente {self.id} ({self.tipo}) se mueve sin rumbo a {nuevo_pos} por pánico")
                        self.x, self.y, self.z = nuevo_pos
                    return

                elif reaccion == "acelerado":
                    self.step_delay = max(1, self.step_delay - 1)
                    print(f"Agente {self.id} ({self.tipo}) acelera por pánico")
            else:
                self.estado_panico = False
                self.step_delay = TIPOS_DE_AGENTE.get(self.tipo, {}).get("delay", 1)
                print(f"Agente {self.id} ({self.tipo}) sale del pánico")

        # Comportamiento emocional de niños
        if self.tipo == "niño" and self.mode == "follow" and self.adulto_referencia:
            adulto = self.adulto_referencia

            if adulto.historial_posiciones:
                target = adulto.historial_posiciones[-1]
                vecinos = self.env.get_neighbors(self.x, self.y, self.z, include_vertical=True)
                seguros = [v for v in vecinos if not self.env.is_on_fire(*v)]

                if target in seguros:
                    self.x, self.y, self.z = target
                    print(f"Niño {self.id} imita al adulto {adulto.id} y se mueve a {target}")

                    if self.env.is_exit(*self.get_position()):
                        self.state = "escaped"
                    return

            # Si niño pierde referencia por pánico, se independiza
            if adulto.state == "dead" or (adulto.state == "escaped" and not adulto.historial_posiciones):
                self.mode = "solo"
                self.adulto_referencia = None
                self.step_delay = 1  # niño entra en mode de escape acelerado
                print(f"Niño {self.id} entra en mode solo y aumenta velocidad por pánico")

        options = self.env.get_neighbors(self.x, self.y, self.z, include_vertical=True)
        safe_moves = [(nx, ny, nz) for (nx, ny, nz) in options if not self.env.is_on_fire(nx, ny, nz)]

        if not safe_moves:
            return  # atrapado

        next_move = self.find_next_move_towards_exit(safe_moves)
        if not next_move:
            return

        if self.env.is_exit(*next_move):
            if self.env.can_exit(*next_move):
                self.env.register_exit(*next_move)
                self.x, self.y, self.z = next_move
                self.state = "escaped"
                self.puerta_salida = next_move
            else:
                self.env.register_waiting_exit(*next_move, self.id)
                self.total_steps_waiting_exit += 1
                self.total_steps_waiting += 1
                return

        elif self.env.is_stairs(*next_move):
            if self.env.can_use_stairs(*next_move):
                self.env.register_stairs(*next_move)
                self.x, self.y, self.z = next_move
                self.escaleras_usadas.append(next_move)
            else:
                self.env.register_waiting_stairs(*next_move, self.id)
                self.total_steps_waiting_stairs += 1
                self.total_steps_waiting += 1
                return

        else:
            if self.env.is_free(*next_move) and self.env.is_cell_free(*next_move):
                self.env.release_agent_position(self.x, self.y, self.z, self.id)
                self.x, self.y, self.z = next_move
                self.env.register_agent_position(self.x, self.y, self.z, self.id)
            else:
                # Si está llena, este movimiento no es válido
                return

    def find_next_move_towards_exit(self, candidates):
        validos = []
        for pos in candidates:
            if self.env.is_on_fire(*pos):
                continue
            if self.env.is_free(*pos) and not self.env.is_cell_free(*pos):
                continue  # Celda llena (2 agentes)
            validos.append(pos)
        
        min_dist = float('inf')
        best_move = None
        for candidate in candidates:
            dist = self.estimate_distance_to_exit(candidate)
            if isinstance(dist, int) and dist < min_dist:
                min_dist = dist
                best_move = candidate
            elif isinstance(dist, tuple):
                return dist
        return best_move

    def estimate_distance_to_exit(self, start):
        visited = set()
        humo_actual = self.env.get_smoke_category(*start)

        if humo_actual == "bajo":
            max_depth = 999
        elif humo_actual == "medio":
            max_depth = 10
        else:
            max_depth = 3

        queue = deque([(start, 0)])
        posibles_seguras_nuevas = []

        while queue:
            (x, y, z), d = queue.popleft()
            if (x, y, z) in visited or d > max_depth:
                continue
            visited.add((x, y, z))

            if self.env.is_exit(x, y, z):
                return d

            for neighbor in self.env.get_neighbors(x, y, z, include_vertical=True):
                if not self.env.is_on_fire(*neighbor):
                    queue.append((neighbor, d + 1))
                    if neighbor not in self.historial_posiciones:
                        posibles_seguras_nuevas.append(neighbor)

        if posibles_seguras_nuevas:
            return random.choice(posibles_seguras_nuevas)

        for pos in reversed(self.historial_posiciones):
            if self.env.is_free(*pos) and not self.env.is_on_fire(*pos):
                return pos

        return None

    @classmethod
    def generate_random_agents(cls, n, env):
        agents = []
        id_counter = 0
        attempts = 0
        max_attempts = 1000
        tipos_posibles = ["niño", "adulto", "anciano"]

        while len(agents) < n and attempts < max_attempts:
            z = random.randint(0, env.n_floors - 1)
            x = random.randint(0, env.height - 1)
            y = random.randint(0, env.width - 1)

            if env.is_free(x, y, z) and not env.is_on_fire(x, y, z):
                if all(a.get_position() != (x, y, z) for a in agents):
                    tipo = random.choice(tipos_posibles)
                    
                    if tipo == "anciano":
                        print(f"Anciano {id_counter}")

                    if tipo == "niño":
                        mode = random.choices(["follow", "solo"],
                                              weights=[TIPOS_DE_AGENTE["niño"]["mode_probability"]["follow"],
                                                       TIPOS_DE_AGENTE["niño"]["mode_probability"]["solo"]])[0]
                        adulto_referencia = None
                        if mode == "follow":
                            adultos = [a for a in agents if a.tipo == "adulto" and a.is_active()]
                            if adultos:
                                adulto_referencia = min(adultos, key=lambda a:
                                    abs(a.x - x) + abs(a.y - y) + abs(a.z - z))
                                print(f"Niño {id_counter} follow a adulto {adulto_referencia.id}")
                            else:
                                mode = "solo"
                                print(f"Niño {id_counter} solo")
                        agent = cls(id=id_counter, x=x, y=y, z=z, env=env,
                                    tipo=tipo, mode=mode, adulto_referencia=adulto_referencia)
                    else:
                        agent = cls(id=id_counter, x=x, y=y, z=z, env=env, tipo=tipo)

                    agents.append(agent)
                    id_counter += 1
            attempts += 1

        if len(agents) < n:
            print(f"Solo se pudieron colocar {len(agents)} agentes de {n} solicitados.")
            
        return agents