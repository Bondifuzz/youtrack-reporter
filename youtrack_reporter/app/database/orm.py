from pydantic import AnyHttpUrl, BaseModel
from typing import Optional

class ORMConfig(BaseModel):
    id: Optional[str]
    '''Unique id of config'''

    update_rev: str
    '''Update operation revision number. Only latest has a sense'''

    url: AnyHttpUrl
    '''Client's YouTrack URL'''

    token: str
    '''Authentication token'''

    project: str
    '''Name of project in YouTrack, where issues would be created'''

    project_id: Optional[str]
    '''Project id inside client's YouTrack'''