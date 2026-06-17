"""
Modulo de inteligencia artificial.

Contiene los agentes de decision en combate:
    - Level1Agent: seleccion aleatoria legal (baseline).
    - Level2Agent: heuristica greedy basada en diferencia de HP.
    - Level3Agent: busqueda Minimax con poda alfa-beta y heuristica simple.
    - Level4Agent: Minimax con heuristica compuesta normalizada.
    - Level5Agent: pesos evolucionados mediante algoritmo genetico.
    - heuristics: funciones de evaluacion puras.
    - genetic_algo: optimizador evolutivo de los pesos del Level5Agent.
"""
