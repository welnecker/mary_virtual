from core.story_models import Beat, Chapter


def _beat(
    beat_id: str,
    line: str,
    next_beat: str | None,
    *,
    gate: str = "",
    route: str,
    completes: tuple[str, ...] = (),
) -> Beat:
    return Beat(
        id=beat_id,
        mary_lines=(line,),
        next_beat=next_beat,
        gate=gate,
        route=route,
        completes=completes,
        instructions=(
            "Use no máximo uma pergunta.",
            "Faça apenas o movimento deste beat.",
        ),
    )


BEATS = {
    "injury_check": _beat(
        "injury_check",
        "Tem certeza que tá tudo bem?",
        "recognize_plaza",
        gate="wellbeing_confirmation",
        route="first_contact",
    ),
    "recognize_plaza": _beat(
        "recognize_plaza",
        "Você por acaso mora no Plaza? Seu rosto não me é estranho...",
        "first_farewell",
        gate="plaza_answer",
        route="first_contact",
        completes=("neighbors_discovered",),
    ),
    "first_farewell": _beat(
        "first_farewell",
        "Tchauzinho...",
        "second_encounter",
        route="first_contact",
        completes=("first_contact_closed",),
    ),
    "second_encounter": _beat(
        "second_encounter",
        "Oi... tá recuperado do susto? rsrsrs",
        "market_crowded",
        route="second_encounter",
    ),
    "market_crowded": _beat(
        "market_crowded",
        "O mercado tá cheio hoje. Essa fila do caixa tá desanimadora.",
        "cart_single_guess",
        route="second_encounter",
    ),
    "cart_single_guess": _beat(
        "cart_single_guess",
        "Tô olhando pro seu carrinho... cerveja, salgadinho e macarrão instantâneo. Isso é típico de solteiro ou passei longe?",
        "home_weekend_routine",
        gate="relationship_answer",
        route="second_encounter",
    ),
    "home_weekend_routine": _beat(
        "home_weekend_routine",
        "Na minha casa é cerveja e futebol quase todo fim de semana. Já acostumei com essa rotina.",
        "checkout_turn",
        route="second_encounter",
    ),
    "checkout_turn": _beat(
        "checkout_turn",
        "Olha, é sua vez no caixa. Passa suas compras.",
        "ask_wait_help_car",
        route="checkout",
    ),
    "ask_wait_help_car": _beat(
        "ask_wait_help_car",
        "Você me espera? Acho que preciso de ajuda até o carro.",
        "open_trunk",
        gate="accept_help_car",
        route="checkout",
    ),
    "open_trunk": _beat(
        "open_trunk",
        "Chegamos. Vou abrir o porta-malas.",
        "liked_meeting",
        route="parking_lot",
        completes=("help_to_car_completed",),
    ),
    "liked_meeting": _beat(
        "liked_meeting",
        "Foi muito legal te conhecer... posso te pedir uma coisa?",
        "request_phone",
        route="parking_lot",
    ),
    "request_phone": _beat(
        "request_phone",
        "Queria seu número. Pra saber se você não ficou com sequelas, sabe? Droga... que desculpa esfarrapada.",
        "exchange_numbers",
        gate="phone_acceptance",
        route="parking_lot",
    ),
    "exchange_numbers": _beat(
        "exchange_numbers",
        "Anota o meu também.",
        "car_farewell",
        route="parking_lot",
        completes=("phone_numbers_exchanged",),
    ),
    "car_farewell": _beat(
        "car_farewell",
        "Tchau... foi um prazer te conhecer.",
        None,
        route="parking_lot",
        completes=("chapter_01_completed",),
    ),
}


CHAPTER = Chapter(
    id="chapter_01",
    title="O encontro no supermercado",
    opening_message="Eita, caralho... desculpa!",
    first_beat="injury_check",
    beats=BEATS,
    ending_message=(
        "Mary encerra esse encontro e segue o próprio caminho. Para viver esta história "
        "novamente, é necessário iniciar uma nova sessão."
    ),
)


__all__ = ["BEATS", "CHAPTER"]
