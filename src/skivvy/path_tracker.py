class PathTracker:
    def __init__(self):
        self._segments = []

    def push(self, segment):
        self._segments.append(segment)

    def pop(self):
        self._segments.pop()

    @property
    def current(self):
        return list(self._segments)
