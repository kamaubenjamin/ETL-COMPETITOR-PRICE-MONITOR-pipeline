"""Fixed safe error codes for upload progress reads."""

from enum import Enum


class UploadProgressErrorCode(str, Enum):
    NOT_FOUND = "upload_progress_not_found"
    INVALID_QUERY = "invalid_upload_progress_query"
    UNSUPPORTED_SOURCE = "unsupported_progress_source"

