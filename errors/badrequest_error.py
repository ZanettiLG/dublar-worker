class BadRequestError(Exception):
    def __init__(self, event, cause, field, value, status=400, message=None):
        self.event = event
        self.cause = cause
        self.field = field
        self.value = value
        self.status = status
        self.message = message
        super().__init__(self.message)

    def __str__(self):
        return f"BadRequestError: {self.cause} - {self.field} - {self.value}"

    def __repr__(self):
        return f"BadRequestError: {self.cause} - {self.field} - {self.value}"


