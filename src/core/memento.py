import random
from contextlib import contextmanager


@contextmanager
def battle_snapshot(p1_team, p2_team, *, capture_rng: bool = True):
    """
    Context manager que aplica el patrón Memento al estado mutable de una batalla.

    Captura HP, status, stat_stages y PP de cada Pokémon de ambos equipos, y
    opcionalmente el estado de random. Al salir del bloque (incluso por excepción)
    se restaura todo al snapshot inicial.

    Args:
        p1_team: lista de Pokémon del jugador 1 (puede ser None).
        p2_team: lista de Pokémon del jugador 2 (puede ser None).
        capture_rng (bool): si True, captura y restaura random.getstate().

    Returns:
        None (se usa como context manager).
    """
    rng_state = random.getstate() if capture_rng else None

    snap: dict = {}
    for p in (p1_team or []) + (p2_team or []):
        snap[id(p)] = (
            p,
            p.current_hp,
            p.status_ailment,
            dict(p.stat_stages),
            tuple(m.current_pp for m in p.moves),
        )

    try:
        yield
    finally:
        if rng_state is not None:
            random.setstate(rng_state)

        for p, hp, ail, stages, pps in snap.values():
            p.current_hp = hp
            p.status_ailment = ail
            p.stat_stages = stages
            for m, pp in zip(p.moves, pps):
                m.current_pp = pp
