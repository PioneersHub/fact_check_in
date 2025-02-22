class NotOk(Exception):
    def __init__(self, status_code, content):
        self.status_code = status_code
        self.content = content
        super().__init__(f"status code: {status_code}, content: {content}")
