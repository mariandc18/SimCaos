import numpy as np
import os
import csv

class Environment:
    FREE = 0
    WALL = 1
    EXIT = 2
    STAIRS = 3
    FIRE_START = 9  

    def __init__(self, planos_dir):
        self.grid = []           
        self.fire_state = []  
        self.smoke_state = []   
        self.n_floors = 0
        self.height = 0
        self.width = 0

        self.exit_capacity = {}      
        self.exit_occupancy = {}      
        self.stairs_capacity = {}    
        self.stairs_occupancy = {}  
        self.occupancy_map = {}  
        
        #estadisticas que se guardan
        self.waiting_exit = {}     
        self.waiting_stairs = {}   

        self.load_building(planos_dir)
        self.validate_building()

    def load_building(self, dir_path):
        files = sorted([f for f in os.listdir(dir_path) if f.endswith(".csv")])
        for file in files:
            with open(os.path.join(dir_path, file), newline='') as csvfile:
                reader = csv.reader(csvfile)
                matrix = [[int(cell) for cell in row] for row in reader]
                matrix_np = np.array(matrix)
                self.grid.append(matrix_np)
                self.fire_state.append(np.zeros_like(matrix_np))
                self.smoke_state.append(np.zeros_like(matrix_np, dtype=float)) 
        
        self.n_floors = len(self.grid)
        self.height, self.width = self.grid[0].shape

    def validate_building(self):
        for z, layer in enumerate(self.grid):
            if layer.shape != (self.height, self.width):
                raise ValueError(f"El piso {z} tiene tamaño inconsistente.")

        total_exits = sum(np.sum(floor == self.EXIT) for floor in self.grid)
        if total_exits == 0:
            raise ValueError("El edificio no tiene ninguna salida definida.")

        for z, layer in enumerate(self.grid):
            if not np.any(layer == self.EXIT):
                print(f"Advertencia: El piso {z} no tiene salida directa.")

        for z in range(self.n_floors - 1):
            stairs_current = np.where(self.grid[z] == self.STAIRS)
            stairs_next = np.where(self.grid[z + 1] == self.STAIRS)
            coords_current = set(zip(stairs_current[0], stairs_current[1]))
            coords_next = set(zip(stairs_next[0], stairs_next[1]))
            if not coords_current & coords_next:
                print(f"Escaleras no alineadas entre piso {z} y {z + 1}")

    def in_bounds(self, x, y, z):
        return (0 <= x < self.height and 0 <= y < self.width and 0 <= z < self.n_floors)

    def get_cell(self, x, y, z):
        return self.grid[z][x][y] if self.in_bounds(x, y, z) else None

    def get_cell_type(self, x, y, z):
        if not self.in_bounds(x, y, z):
            return "out_of_bounds"
        val = self.grid[z][x][y]
        return {
            self.FREE: "free",
            self.WALL: "wall",
            self.EXIT: "exit",
            self.STAIRS: "stairs",
            self.FIRE_START: "fire_start"
        }.get(val, "unknown")

    def is_free(self, x, y, z):
        return self.in_bounds(x, y, z) and self.grid[z][x][y] == self.FREE

    def is_exit(self, x, y, z):
        return self.in_bounds(x, y, z) and self.grid[z][x][y] == self.EXIT

    def is_stairs(self, x, y, z):
        return self.in_bounds(x, y, z) and self.grid[z][x][y] == self.STAIRS

    def is_on_fire(self, x, y, z):
        return self.in_bounds(x, y, z) and self.fire_state[z][x][y] == self.FIRE_START

    def set_fire(self, x, y, z):
        if self.in_bounds(x, y, z):
            self.fire_state[z][x][y] = self.FIRE_START

    def reset_fire(self):
        self.fire_state = [np.zeros_like(f) for f in self.fire_state]
       
    #resetea el humo    
    def reset_smoke(self):  
        self.smoke_state = [np.zeros_like(f, dtype=float) for f in self.grid]
        
    def get_smoke_category(self, x, y, z):
        level = self.smoke_state[z][x][y]
        if level < 0.3:
            return "bajo"
        elif level < 0.7:
            return "medio"
        else:
            return "alto"

    def set_cell(self, x, y, z, value):
        if self.in_bounds(x, y, z):
            self.grid[z][x][y] = value

    def get_neighbors(self, x, y, z, include_vertical=True):
        directions = [(-1, 0), (1, 0), (0, -1), (0, 1)]
        neighbors = []

        for dx, dy in directions:
            nx, ny = x + dx, y + dy
            if self.is_free(nx, ny, z) or self.is_exit(nx, ny, z):
                neighbors.append((nx, ny, z))

        if include_vertical and self.is_stairs(x, y, z):
            for dz in [-1, 1]:
                nz = z + dz
                if 0 <= nz < self.n_floors and self.is_stairs(x, y, nz):
                    neighbors.append((x, y, nz))

        return neighbors

    def get_all_exits(self):
        exits = []
        for z in range(self.n_floors):
            positions = np.argwhere(self.grid[z] == self.EXIT)
            exits.extend([(x, y, z) for x, y in positions])
        return exits

    def get_all_stairs(self):
        stairs = []
        for z in range(self.n_floors):
            positions = np.argwhere(self.grid[z] == self.STAIRS)
            stairs.extend([(x, y, z) for x, y in positions])
        return stairs

    def get_dimensions(self):
        return self.height, self.width, self.n_floors

    def print_floor(self, z):
        print(f"Piso {z}:")
        for row in self.grid[z]:
            print(" ".join(str(cell) for cell in row))

    def set_exit_capacity(self, x, y, z, cap):
        self.exit_capacity[(x, y, z)] = cap

    def set_stairs_capacity(self, x, y, z, cap):
        self.stairs_capacity[(x, y, z)] = cap

    def reset_occupancy(self):
        self.exit_occupancy = {pos: 0 for pos in self.exit_capacity}
        self.stairs_occupancy = {pos: 0 for pos in self.stairs_capacity}
        
    #funcion para las estadisticas de espera
    def reset_waiting_lists(self):
        self.waiting_exit = {pos: [] for pos in self.exit_capacity}
        self.waiting_stairs = {pos: [] for pos in self.stairs_capacity}

    def can_exit(self, x, y, z):
        key = (x, y, z)
        cap = self.exit_capacity.get(key)
        occ = self.exit_occupancy.get(key, 0)
        return cap is None or occ < cap

    def register_exit(self, x, y, z):
        key = (x, y, z)
        if key in self.exit_capacity:
            self.exit_occupancy[key] = self.exit_occupancy.get(key, 0) + 1

    def can_use_stairs(self, x, y, z):
        key = (x, y, z)
        cap = self.stairs_capacity.get(key)
        occ = self.stairs_occupancy.get(key, 0)
        return cap is None or occ < cap

    def register_stairs(self, x, y, z):
        key = (x, y, z)
        if key in self.stairs_capacity:
            self.stairs_occupancy[key] = self.stairs_occupancy.get(key, 0) + 1
                  
    def register_waiting_exit(self, x, y, z, agent_id):
        key = (x, y, z)
        if key in self.waiting_exit:
            self.waiting_exit[key].append(agent_id)

    def register_waiting_stairs(self, x, y, z, agent_id):
        key = (x, y, z)
        if key in self.waiting_stairs:
            self.waiting_stairs[key].append(agent_id)
            
    def is_cell_free(self, x, y, z):
        ocupantes = self.occupancy_map.get((x, y, z), [])
        return len(ocupantes) < 2

    def register_agent_position(self, x, y, z, agent_id):
        key = (x, y, z)
        if key not in self.occupancy_map:
            self.occupancy_map[key] = [agent_id]
        else:
            if agent_id not in self.occupancy_map[key]:
                self.occupancy_map[key].append(agent_id)

    def release_agent_position(self, x, y, z, agent_id):
        key = (x, y, z)
        if key in self.occupancy_map:
            if agent_id in self.occupancy_map[key]:
                self.occupancy_map[key].remove(agent_id)
            if len(self.occupancy_map[key]) == 0:
                del self.occupancy_map[key]
    def reset_occupancy_map(self):
        self.occupancy_map = {}

