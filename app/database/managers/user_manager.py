import bcrypt
from core.logger import app_logger
from database.managers.base_manager import BaseManager
from database.managers.session_manager import manager
from database.models.user import User
from exceptions.base import DatabaseError
from exceptions.users import InvalidCredentialsError
from exceptions.users import UserAlreadyExistsError
from exceptions.users import UserNotFoundError
from schemas.user import UpdateUser
from schemas.user import UserAuth
from schemas.user import UserCreate
from sqlalchemy.exc import IntegrityError
from sqlalchemy.future import select

class UserManager(BaseManager[User, UpdateUser]):
    def __init__(self) -> None:
        super().__init__(User)

    @staticmethod
    async def get_user_by_login(login: str) -> User:
        async with manager.get_async_session() as session:
            result = await session.execute(select(User).where(User.login == login))
            user = result.scalars().first()
            if user is None:
                raise UserNotFoundError()
            return user

    @staticmethod
    async def get_user_id_by_login(login: str) -> int:
        user = await UserManager.get_user_by_login(login)
        return getattr(user, "id", 0)

    @staticmethod
    async def create_user(user_create: UserCreate) -> User:
        password = user_create.password
        obj_dict = user_create.model_dump(exclude={"password"})
        user = User(**obj_dict)
        setattr(user, "password_hash", UserManager._hash_password(password))
        async with manager.get_async_session() as session:
            try:
                session.add(user)
                await session.commit()
                await session.refresh(user)
                return user
            except IntegrityError:
                await session.rollback()
                app_logger.warning_event("user_create_conflict", login=user_create.login)
                raise UserAlreadyExistsError()
            except Exception as e:
                await session.rollback()
                app_logger.error_event("user_create_failed", login=user_create.login)
                raise DatabaseError()

    @staticmethod
    async def search_users(query: str, skip: int = 0, limit: int = 100):
        async with manager.get_async_session() as session:
            result = await session.execute(
                select(User)
                .where(User.login.ilike(f"%{query}%"))
                .offset(skip)
                .limit(limit)
            )
            return result.scalars().all()

    @staticmethod
    async def check_user_data(user: UserAuth) -> User:
        db_user = await UserManager.get_user_by_login(user.login)
        if not db_user:
            app_logger.warning_event("user_login_user_not_found", login=user.login)
            raise UserNotFoundError()
        db_password_hash = getattr(db_user, "password_hash", None)
        if db_password_hash and bcrypt.checkpw(user.password.encode("utf-8"),
                                               db_password_hash.encode("utf-8")):
            return db_user
        app_logger.warning_event("user_login_invalid_credentials", login=user.login)
        raise InvalidCredentialsError()
    
    @staticmethod
    def _hash_password(password: str) -> str:
        return bcrypt.hashpw(password.encode("utf-8"),
                             bcrypt.gensalt()).decode("utf-8")
