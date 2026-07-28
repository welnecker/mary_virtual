from stories.casada_frustrada import package as casada_frustrada_package


def register_builtin_stories() -> None:
    from catalog import register_story

    register_story(casada_frustrada_package, replace=True)


__all__ = ["register_builtin_stories"]
