class SourceRoom:
    """Represents a single Celeste room."""

    def __init__(self, id):
        self.id = id

        self.locations = []
        self.next_rooms = []
        self.parent_room_paths = []