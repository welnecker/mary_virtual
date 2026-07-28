from core.story_models import StoryManifest


MANIFEST = StoryManifest(
    id="casada_frustrada",
    title="Casada frustrada",
    description=(
        "Um encontro casual desperta em Mary uma possibilidade que ela não esperava. "
        "A história acompanha toda a aproximação, das compras ao contato privado e ao "
        "desfecho final, dentro da mesma execução."
    ),
    price_cents=990,
    currency="BRL",
    chapter_ids=("full_story",),
    card_image="stories/casada_frustrada/assets/card.webp",
    adult_only=True,
    active=True,
)


__all__ = ["MANIFEST"]
