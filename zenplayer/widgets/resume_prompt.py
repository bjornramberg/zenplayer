from rich.text import Text
from textual.widget import Widget


class ResumePrompt(Widget):
    can_focus = True

    def __init__(self):
        super().__init__()
        self._show = False

    def render(self) -> Text:
        if not self._show:
            return Text("")
        text = Text()
        text.append("  Press ", style="dim")
        text.append("r", style="bold")
        text.append(" to resume · Press any other key to search", style="dim")
        return text

    def show(self):
        self._show = True
        self.refresh()

    def hide(self):
        self._show = False
        self.refresh()
