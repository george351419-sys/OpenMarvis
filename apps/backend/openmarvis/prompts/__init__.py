from importlib.resources import files


def load_prompt(name: str) -> str:
    return (files(__package__) / f"{name}.md").read_text(encoding="utf-8")
