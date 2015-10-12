
# This is potentially overriden by theming logic, sensible defaults (not) provided
OPERATOR_COLORS = {}

CHAT_COLORS = {
    "default": "grey"
}

def getColor(name):
    if name in CHAT_COLORS:
        return CHAT_COLORS[name]
    else:
        return CHAT_COLORS["default"]
