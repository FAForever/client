
# This is potentially overriden by theming logic, sensible defaults provided
OPERATOR_COLORS = {"~": "#FFFFFF",
                   "&": "#FFFFFF",
                   "@": "#FFFFFF",
                   "%": "#FFFFFF",
                   "+": "#FFFFFF"}


CHAT_COLORS = {
    "default": "grey"
}

def getColor(name):
    if name in CHAT_COLORS:
        return CHAT_COLORS[name]
    else:
        return CHAT_COLORS["default"]
