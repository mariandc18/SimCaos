import numpy as np
from model.environment import Environment

class FireManager:
    def __init__(self, environment: Environment):
        self.env = environment
        self.burning_cells = set()
        self.wall_delay = 3
        self.exposed_cells = dict()

        self.IGNITION_PROBS = {
            Environment.FREE: 0.8,
            Environment.STAIRS: 0.6,
            Environment.EXIT: 0.4,
            Environment.WALL: 0.2,
        }

        self.tiempo_umbral_vertical = 6 

    def ignite(self, x, y, z):
        """Enciende una celda si no está ya en llamas."""
        if self.env.in_bounds(x, y, z) and not self.env.is_on_fire(x, y, z):
            self.env.set_fire(x, y, z) 
            self.burning_cells.add((x, y, z))

    def ignite_all_fire_starts(self):
        """Enciende todas las celdas marcadas como FIRE_START en la grilla."""
        for z in range(self.env.n_floors):
            positions = np.argwhere(self.env.grid[z] == self.env.FIRE_START)
            for x, y in positions:
                self.ignite(x, y, z)

    def step(self):
        """Actualiza el estado del fuego, propagando y aumentando tiempos."""
        new_burning = set()

        for (x, y, z) in self.burning_cells:
            self.env.fire_state[z][x][y] += 1
            tiempo = self.env.fire_state[z][x][y]

            for dx, dy in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
                nx, ny = x + dx, y + dy
                if self.env.in_bounds(nx, ny, z) and not self.env.is_on_fire(nx, ny, z):
                    tipo = self.env.grid[z][nx][ny]
                    prob = self.IGNITION_PROBS.get(tipo, 0.0)

                    if tipo == Environment.WALL:
                        key = (nx, ny, z)
                        self.exposed_cells[key] = self.exposed_cells.get(key, 0) + 1

                        if self.exposed_cells[key] >= self.wall_delay:
                            if prob > 0 and np.random.rand() < prob:
                                new_burning.add(key)
                                del self.exposed_cells[key] 
                    else:
                        if prob > 0 and np.random.rand() < prob:
                            new_burning.add((nx, ny, z))

            nz = z + 1
            if self.env.in_bounds(x, y, nz) and not self.env.is_on_fire(x, y, nz):
                tipo_superior = self.env.grid[nz][x][y]
                prob_superior = self.IGNITION_PROBS.get(tipo_superior, 0.0)
                if tiempo >= self.tiempo_umbral_vertical:
                    if prob_superior > 0 and np.random.rand() < prob_superior:
                        new_burning.add((x, y, nz))

            nz = z - 1
            if self.env.in_bounds(x, y, nz) and not self.env.is_on_fire(x, y, nz):
                tipo_inferior = self.env.grid[nz][x][y]
                prob_inferior = self.IGNITION_PROBS.get(tipo_inferior, 0.0)
                if tiempo >= self.tiempo_umbral_vertical:
                    if prob_inferior > 0 and np.random.rand() < prob_inferior:
                        new_burning.add((x, y, nz))

        # Enciende las nuevas celdas
        for (nx, ny, nz) in new_burning:
            self.ignite(nx, ny, nz)
            self.exposed_cells.pop((nx, ny, nz), None)  # Elimina si estaba en espera

        # Actualiza el conjunto de celdas en llamas
        self.burning_cells.update(new_burning)
        self.update_smoke_levels()

    # Función que calcula la cantidad de humo por proximidad al fuego
    def update_smoke_levels(self):
        for z in range(self.env.n_floors):
            for x in range(self.env.height):
                for y in range(self.env.width):
                    if self.env.is_free(x, y, z):
                        min_dist = None
                        for (fx, fy, fz) in self.burning_cells:
                            dist = abs(fx - x) + abs(fy - y) + abs(fz - z)
                            if min_dist is None or dist < min_dist:
                                min_dist = dist
                        if min_dist is None:
                            level = 0.0
                        elif min_dist <= 2:
                            level = 1.0  # Alto
                        elif min_dist <= 5:
                            level = 0.6  # Medio
                        else:
                            level = 0.2  # Bajo
                        self.env.smoke_state[z][x][y] = level