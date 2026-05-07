# PokePikas - Simulador de Batallas Pokémon

PokePikas es un simulador de batallas Pokémon desarrollado en **Python** utilizando la librería **Pygame**. El proyecto utiliza datos dinámicos obtenidos directamente de [PokéAPI](https://pokeapi.co/) para recrear la experiencia de combate, permitiendo tanto el juego con interfaz gráfica como simulaciones automatizadas entre agentes de IA.

##  Resumen
El proyecto integra un motor de batalla completo, gestión de estados, y agentes inteligentes. 


##  Requisitos Previos
Asegúrate de tener instalados los siguientes componentes:
* **Python 3.7** o superior.
* **Pip** (gestor de paquetes de Python).

##  Instalación

Sigue estos pasos para configurar el entorno local:

### 1. Clonar el repositorio
git clone [https://github.com/kuki236/PokePikas.git](https://github.com/kuki236/PokePikas.git)  
cd PokePikas

### 2. Instalar dependencias
pip install -r requirements.txt

## Ejecución del Juego

Opción 1: Interfaz Gráfica (Menú Principal)
Para iniciar la experiencia completa con menús y visualización:

python src/gui/menu.py

Opción 2: Simulación de IA (Sin Interfaz)
Para ejecutar pruebas de rendimiento y batallas automatizadas entre agentes de Inteligencia Artificial:

python simulate_ai_2.py

## Estructura del Proyecto

PokePikas/  
├── src/  
│   ├── gui/           # Interfaz gráfica y menús  
│   ├── core/          # Motor lógico de la batalla  
│   ├── ai/            # Agentes de IA (Minimax, Algoritmos Genéticos)  
│   ├── entities/      # Clases base de Pokémon y Movimientos  
│   └── utils/         # Utilidades de carga de datos (DataLoader)  
├── data/              # Archivos JSON generados post-fetch  
├── assets/            # Recursos visuales y sonoros  
├── fetch_data.py      # Script de conexión con PokéAPI  
├── simulate_ai_2.py   # Simulador de batallas entre IAs  
└── requirements.txt   # Dependencias del proyecto
