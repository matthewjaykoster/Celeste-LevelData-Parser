class SourceRoom:
    """Represents some data from a single Celeste room."""

    def __init__(self, id):
        self.id = id

        self.next_rooms = []
