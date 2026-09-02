# 🔥 SimCaos

Simulación basada en agentes de evacuación de un edificio ante un incendio, con propagación de fuego y humo como evaluación final de la asignatura Simulación.

---

## 📋 Descripción

El sistema simula cómo distintos tipos de agentes (adultos, niños y ancianos) evacuan un edificio en presencia de un incendio activo. El fuego se propaga por las celdas del edificio y afecta las decisiones de movimiento de los agentes. Se ejecutan múltiples réplicas hasta alcanzar un **intervalo de confianza del 95%** con error relativo menor al 5%.

---

## Tipos de agentes

- **Adulto** : comportamiento estándar, puede entrar en pánico
- **Anciano** : movimiento más lento (delay mayor)
- **Niño** : puede seguir a un adulto de referencia (`follow`) o moverse de forma independiente (`solo`)

### Estados emocionales
- **Pánico** : parálisis, movimiento desorientado o acelerado
- **Reacción tardía** : algunos agentes demoran en reaccionar al inicio

---

## Tipos de celda en el edificio

| Valor | Tipo |
|---|---|
| `0` | Celda libre |
| `1` | Pared |
| `2` | Salida |
| `3` | Escaleras |
| `9` | Foco de incendio |

---

## Propagación del fuego

- Se propaga horizontalmente con probabilidades según el tipo de celda
- Las paredes requieren exposición sostenida antes de encenderse (`wall_delay`)
- La propagación vertical entre plantas ocurre tras un umbral de tiempo (`tiempo_umbral_vertical`)
- El humo se calcula por proximidad al fuego en cada paso

---

## 🚀 Ejecución

```bash
python main.py
```

---

Los resultados se guardan en la carpeta `resultados/`:
- `resultados_globales.json` — métricas por réplica
- `resultados_agentes.json` — estadísticas individuales por agente
