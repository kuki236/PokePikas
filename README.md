# PokePikas — Documentación Técnica

## 1. Introducción

PokePikas es un simulador de batallas Pokémon desarrollado en Python con la librería Pygame. El proyecto utiliza datos obtenidos desde PokéAPI para recrear un sistema de combate por turnos, ofreciendo dos experiencias principales: juego con interfaz gráfica y simulaciones automatizadas entre agentes de inteligencia artificial.

El objetivo del proyecto es servir como una base reproducible para estudiar mecánicas de combate, evaluación de estados, heurísticas, búsqueda Minimax y algoritmos genéticos en un entorno lúdico y educativo.

## 2. Objetivo del proyecto

El proyecto busca:

- Recrear batallas Pokémon con una estructura modular.
- Permitir la interacción mediante interfaz gráfica.
- Ejecutar simulaciones automáticas entre agentes IA.
- Evaluar estrategias de combate mediante benchmarks.

## 3. Requisitos previos

Antes de ejecutar el proyecto, asegúrate de tener instalado:

- Python 3.7 o superior.
- Pip para la gestión de paquetes.

## 4. Instalación

### 4.1 Clonar el repositorio

```bash
git clone https://github.com/kuki236/PokePikas.git
cd PokePikas
```

### 4.2 Instalar dependencias

```bash
pip install -r requirements.txt
```

Las dependencias principales son:

- `pygame==2.6.1`
- `requests>=2.25.0`

## 5. Ejecución

### 5.1 Interfaz gráfica

Para iniciar la experiencia visual completa:

```bash
python src/gui/menu.py
```

Desde este menú se puede elegir el modo de juego, el tamaño del equipo, el nivel de la IA y luego acceder a la pantalla de batalla.

### 5.2 Simulación de IA

Para ejecutar batallas automatizadas sin interfaz gráfica:

```bash
python simulate_ai_2.py
python simulate_ai_4.py
python simulate_ai_5.py
```

También existen scripts adicionales para pruebas más avanzadas y benchmarking de agentes.

## 6. Estructura del proyecto

```text
PokePikas/
├── src/
│   ├── gui/           # Interfaz gráfica y menús
│   ├── core/          # Motor lógico de la batalla
│   ├── ai/            # Agentes de IA (Minimax, algoritmos genéticos)
│   ├── entities/      # Clases base de Pokémon y movimientos
│   └── utils/         # Utilidades
├── data/              # Archivos JSON generados
├── assets/            # Recursos visuales y sonoros
├── fetch_data.py      # Script de conexión con PokéAPI
├── simulate_ai_2.py   # Simulador de batallas entre IAs
└── requirements.txt   # Dependencias del proyecto
```

## 7. Arquitectura general

El sistema se organiza en capas para separar responsabilidades:

- **Capa de datos**: persisten los datos obtenidos desde PokéAPI.
- **Capa de entidades**: define Pokémon, movimientos, estados y tipos.
- **Capa core**: maneja el combate, el cálculo de daño y la lógica de turnos.
- **Capa de IA**: implementa agentes de decisión con distintos niveles de complejidad.
- **Capa de presentación**: renderiza menús, batallas y efectos visuales con Pygame.

## 8. Flujo de funcionamiento

El flujo principal del proyecto es el siguiente:

1. `DataLoader` carga los JSON y crea objetos de combate.
2. `menu.py` permite seleccionar modo, equipo y dificultad.
3. `battle_engine.py` ejecuta el combate por turnos.
4. Los agentes IA seleccionan acciones según el `BattleState`.
5. `Renderer` dibuja la interfaz visual y los efectos.

## 9. Componentes principales

### 9.1 Entidades

- `Pokemon`: representa un Pokémon en combate con HP, estadísticas, tipos, movimientos, estados alterados y stages.
- `Move`: representa un movimiento con poder, precisión, tipo, PP y efectos secundarios.
- `PokemonType` y `AilmentType`: enumeraciones para tipos y estados.

### 9.2 Core de batalla

- `BattleState`: estado completo del combate.
- `Action` y `ActionType`: representan una acción de movimiento o cambio.
- `process_turn()`: resuelve un turno completo.
- `calculate_damage()`: calcula el daño final considerando tipos, estadísticas y modificadores.

### 9.3 IA

El proyecto incluye cinco niveles de agentes:

- **Level 1**: selección aleatoria legal.
- **Level 2**: heurística local basada en daño y vida restante.
- **Level 3**: búsqueda Minimax con evaluación simple.
- **Level 4**: Minimax con heurística más completa y selección inteligente de acciones.
- **Level 5**: IA optimizada por algoritmo genético con pesos evolucionados.

### 9.4 Interfaz gráfica

- `menu.py`: gestiona el flujo del menú principal.
- `renderer.py`: centraliza el dibujo de texto, botones, barras de vida, sprites y efectos.
- `battle_ui.py`: controla la pantalla de combate.

### 9.5 Utilidades

- `data_loader.py`: carga Pokémon y movimientos desde archivos JSON.
- `move_registry.py`: mantiene plantillas de movimientos reutilizables.

## 10. Datos y persistencia

El proyecto usa una carpeta `data/` como fuente local. Allí se almacenan:

- `pokemon_pool.json`
- `moves_pool.json`
- `data/ai/level5_weights.json`

Esto permite ejecutar el juego sin depender de una conexión continua a internet.

## 11. Simulaciones y benchmarking

Además del modo jugable, el proyecto incluye scripts para ejecutar simulaciones de IA y comparar el rendimiento entre agentes. Esto permite evaluar win rate, turnos promedio, HP restante y comportamiento táctico entre estrategias.

## 12. Reproducibilidad

El código está estructurado para que cualquier persona pueda reproducir el proyecto siguiendo los pasos de instalación, generación de datos y ejecución. El uso de archivos JSON, scripts separados y una arquitectura modular facilita tanto la comprensión como la extensión del sistema.

## 13. Conclusión

PokePikas es un proyecto que combina desarrollo de videojuegos, modelado orientado a objetos, IA aplicada y simulación reproducible. Su diseño modular permite usarlo tanto como juego interactivo como plataforma de experimentación para comparar estrategias de combate.

## 14. Referencias

- PokéAPI: https://pokeapi.co/
- Pygame: https://www.pygame.org/
- Repositorio del proyecto: https://github.com/kuki236/PokePikas
