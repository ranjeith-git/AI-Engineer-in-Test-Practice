"""Project root discovery: everything is anchored to Chapter03_Local_TC_Gen/."""

from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SRC_DIR = PROJECT_ROOT / "src"
ENV_PATH = SRC_DIR / ".env"
TEMPLATE_DIR = PROJECT_ROOT / "templates"
# The spec (src/Finetuned_prompt.md) names the runtime template literally as
# "template/test cases creator.md" — spaces included. That file is the single
# source of truth for generated output format.
DEFAULT_TEMPLATE_FILE = TEMPLATE_DIR / "test cases creator.md"
PROMPTS_DIR = SRC_DIR / "prompts"
LOG_PATH = PROJECT_ROOT / "app.log"
