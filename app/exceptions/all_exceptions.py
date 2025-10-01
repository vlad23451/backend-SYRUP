from .base import DatabaseError 
from .base import ModelNotFoundError 
from .base import PermissionError
from .base import UnknownDatabaseError
from .base import ValidationError

from .comments import CommentNotFoundError
from .comments import OwnershipCommentError

from .favorites import FavoriteAlreadyExistsError
from .favorites import FavoriteNotFoundError
from .favorites import OwnershipFavoriteError

from .follows import FollowAlredyExists

from .histories import HistoryNotFoundError
from .histories import OwnershipHistoryError

from .history_views import HistoryViewAlreadyExistsError
from .history_views import HistoryViewNotFoundError

from .likes import CommentDislikeNotFoundError
from .likes import CommentLikeNotFoundError
from .likes import DislikeNotFoundError
from .likes import LikeNotFoundError
from .likes import OwnershipCommentDislikeError
from .likes import OwnershipCommentLikeError
from .likes import OwnershipDislikeError
from .likes import OwnershipLikeError

from .media_files import MediaFileAccessDeniedError
from .media_files import MediaFileHistoryAttachError
from .media_files import MediaFileNotFoundError
from .media_files import MediaFileOperationError
from .media_files import MediaFileSizeExceededError
from .media_files import MediaFileTypeNotSupportedError
from .media_files import MediaFileUploadError
from .media_files import MediaFileValidationError

from .messages import MessageNotFoundError
from .messages import OwnershipMessageError

from .s3 import S3ObjectNotFoundError
from .s3 import S3ServiceUnavailableError
from .s3 import S3UploadError
from .s3 import S3ValidationError

from .user_blocks import UserAlreadyBlockedError
from .user_blocks import UserBlockNotFoundError
from .user_blocks import UserSelfBlockError

from .users import InvalidCredentialsError
from .users import InvalidOldPasswordError
from .users import InvalidUserDataError
from .users import UserAlreadyExistsError
from .users import UserNotFoundAvatar
from .users import UserNotFoundError

KNOWN_EXCEPTIONS = (
    DatabaseError,
    ModelNotFoundError,
    PermissionError,
    UnknownDatabaseError,
    ValidationError,

    CommentNotFoundError,
    OwnershipCommentError,

    FavoriteAlreadyExistsError,
    FavoriteNotFoundError,
    OwnershipFavoriteError,

    FollowAlredyExists,

    HistoryNotFoundError,
    OwnershipHistoryError,

    HistoryViewAlreadyExistsError,
    HistoryViewNotFoundError,

    CommentDislikeNotFoundError,
    CommentLikeNotFoundError,
    DislikeNotFoundError,
    LikeNotFoundError,
    OwnershipCommentDislikeError,
    OwnershipCommentLikeError,
    OwnershipDislikeError,
    OwnershipLikeError,

    MediaFileAccessDeniedError,
    MediaFileHistoryAttachError,
    MediaFileNotFoundError,
    MediaFileOperationError,
    MediaFileSizeExceededError,
    MediaFileTypeNotSupportedError,
    MediaFileUploadError,
    MediaFileValidationError,

    MessageNotFoundError,
    OwnershipMessageError,

    S3ObjectNotFoundError,
    S3ServiceUnavailableError,
    S3UploadError,
    S3ValidationError,

    UserAlreadyBlockedError,
    UserBlockNotFoundError,
    UserSelfBlockError,

    InvalidCredentialsError,
    InvalidOldPasswordError,
    InvalidUserDataError,
    UserAlreadyExistsError,
    UserNotFoundAvatar,
    UserNotFoundError,
)
