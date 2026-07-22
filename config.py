MODEL_DEFAULT = "google/gemini-3-flash-preview"
OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"
MARY_SPREADSHEET_ID = (
    "1lOd92EhC-UZmK48kYS-Q_HYO9qpRU5BxpM2uUlVWD-g"
)

# Uma historinha pode chegar a aproximadamente 50 interações.
# Cada interação produz duas mensagens (usuário + Mary), além da abertura.
# A margem evita que o início da história seja removido do contexto antes
# do encerramento, inclusive quando o limite rígido do cenário é utilizado.
MAX_HISTORY_MESSAGES = 120

MAX_IMAGE_SIZE_MB = 8
MAX_IMAGE_DIMENSION = 1024
IMAGE_JPEG_QUALITY = 82

REQUEST_TIMEOUT_SECONDS = 120

APP_TITLE = "Mary Virtual"
APP_CAPTION = "Conversa multimodal com texto e fotografia."

APP_VERSION = "mary-app-v1"
PROMPT_VERSION = "mary-prompt-v1"
