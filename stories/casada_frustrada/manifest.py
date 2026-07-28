from core.story_models import StoryManifest


MANIFEST = StoryManifest(
    id="casada_frustrada",
    title="Casada frustrada",
    description=(
        "Um encontro casual desperta em Mary uma possibilidade que ela não esperava. "
        "A aproximação cresce em capítulos independentes, sempre guiados pelo roteiro."
    ),
    price_cents=990,
    currency="BRL",
    chapter_ids=("chapter_01",),
    card_image="stories/casada_frustrada/assets/card.webp",
    adult_only=True,
    active=True,
)


__all__ = ["MANIFEST"]
