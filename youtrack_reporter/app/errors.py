class YouTrackError(Exception):
    pass

class ResponseStatusError(YouTrackError):
    def __init__(self, code):
        self.status_code = code
        self.message = f"Response status code is {code} - not OK"
        super().__init__(self.message)

class ProjectNotFound(YouTrackError):
    def __init__(self, project: str):
        self.project = project
        self.message = f"No project \"{self.project}\" found"
        super().__init__(self.message)

class TooManyProjectsFound(YouTrackError):
    def __init__(self, project: str):
        self.project = project
        self.message = f"Found few projects \"{self.project}\" and can't decide what to use"
        super().__init__(self.message)
class JsonIsNotList(YouTrackError):
    def __init__(self, resp: str):
        self.resp = resp
        self.message = f"Response json is not a dict, raw resp: {resp}"
        super().__init__(self.message)

class ResponseParseError(YouTrackError):
    def __init__(self, message: str) -> None:
        self.message = message
        super().__init__(self.message)

class ProjectResponseDoesNotMatches(YouTrackError):
    pass

class IssueResponseDoesNotMatches(YouTrackError):
    pass