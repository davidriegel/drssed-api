from pydantic import BaseModel, ConfigDict

class FileReference(BaseModel):
    """A file ID that's referenced somewhere in the database."""
    model_config = ConfigDict(frozen=True)
    
    file_id: str


class LockResult(BaseModel):
    """Result of a MySQL advisory lock attempt."""
    model_config = ConfigDict(frozen=True)
    
    acquired: int