# Código para generar el CSV completo
import csv

with open("floor_plan.csv", mode="w", newline="") as file:
    writer = csv.writer(file)
    writer.writerow(["floor", "x", "y", "type"])

    for piso in range(5):
        for x in range(20):
            for y in range(20):
                # Paredes exteriores
                if x == 0 or x == 19 or y == 0 or y == 19:
                    tipo = "W"
                # Escalera central
                elif x == 10 and y == 10:
                    tipo = "E"
                # Habitaciones en zona norte
                elif y < 6: 
                    tipo = "H"
                # Habitaciones en zona sur
                elif y > 13:
                    tipo = "H"
                # Pasillos centrales
                else:
                    tipo = "P"

                # Salidas solo en planta baja
                if piso == 0 and ((x == 0 and y in [0, 19]) or (x == 19 and y in [0, 19])):
                    tipo = "S"

                writer.writerow([piso, x, y, tipo])
