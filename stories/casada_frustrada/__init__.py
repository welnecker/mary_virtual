from catalog import StoryPackage

from .chapter_01 import CHAPTER
from .manifest import MANIFEST
from .mary_profile import MARY_PROFILE


package = StoryPackage(
    manifest=MANIFEST,
    profile=MARY_PROFILE,
    chapters={CHAPTER.id: CHAPTER},
)


__all__ = ["package"]
