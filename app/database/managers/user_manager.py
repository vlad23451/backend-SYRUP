import bcrypt

from sqlalchemy.exc import IntegrityError
from sqlalchemy.future import select
from sqlalchemy.orm import joinedload

from core.logger import app_logger

from database.managers.base_manager import BaseManager
from database.managers.session_manager import manager
from database.models.user import User
from database.models.followers import Follower

from exceptions.base import DatabaseError
from exceptions.users import InvalidCredentialsError
from exceptions.users import InvalidOldPasswordError
from exceptions.users import UserAlreadyExistsError
from exceptions.users import UserNotFoundError

from schemas.user import UpdateUser
from schemas.user import UserAuth
from schemas.user import UserCreate

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
    async def get_user_by_login_with_relations(login: str) -> User:
        """Получить пользователя по логину с загрузкой всех отношений"""
        async with manager.get_async_session() as session:
            result = await session.execute(
                select(User)
                .where(User.login == login)
                .options(
                    joinedload(User.initiated_friendships),
                    joinedload(User.received_friendships)
                )
            )
            user = result.scalars().first()
            if user is None:
                raise UserNotFoundError()
            
            # Загружаем DynamicMapped отношения отдельно
            # followers - кто подписан на этого пользователя
            followers_result = await session.execute(
                select(Follower.follower_id).where(Follower.user_id == user.id)
            )
            user._followers_ids = [row[0] for row in followers_result.fetchall()]
            
            # following - на кого подписан этот пользователь
            following_result = await session.execute(
                select(Follower.user_id).where(Follower.follower_id == user.id)
            )
            user._following_ids = [row[0] for row in following_result.fetchall()]
            
            return user

    @staticmethod
    async def get_user_by_id_with_relations(user_id: int) -> User:
        """Получить пользователя по ID с загрузкой всех отношений"""
        async with manager.get_async_session() as session:
            result = await session.execute(
                select(User)
                .where(User.id == user_id)
                .options(
                    joinedload(User.initiated_friendships),
                    joinedload(User.received_friendships)
                )
            )
            user = result.scalars().first()
            if user is None:
                raise UserNotFoundError()
            
            # Загружаем DynamicMapped отношения отдельно
            # followers - кто подписан на этого пользователя
            followers_result = await session.execute(
                select(Follower.follower_id).where(Follower.user_id == user.id)
            )
            user._followers_ids = [row[0] for row in followers_result.fetchall()]
            
            # following - на кого подписан этот пользователь
            following_result = await session.execute(
                select(Follower.user_id).where(Follower.follower_id == user.id)
            )
            user._following_ids = [row[0] for row in following_result.fetchall()]
            
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
    async def search_users_with_filters(query: str, skip: int = 0, limit: int = 100, 
                                       me_user_id: int = None, friends_only: bool = False,
                                       followers_only: bool = False, following_only: bool = False):
        """Поиск пользователей с фильтрацией по друзьям, подписчикам и подпискам"""
        async with manager.get_async_session() as session:
            base_query = select(User).where(User.login.ilike(f"%{query}%"))
            
            # Если ищем только среди друзей
            if friends_only and me_user_id:
                from database.models.friends import Friend
                friends_subquery = select(Friend.friend_id).where(Friend.user_id == me_user_id).union(
                    select(Friend.user_id).where(Friend.friend_id == me_user_id)
                )
                base_query = base_query.where(User.id.in_(friends_subquery))
            
            # Если ищем только среди подписчиков
            elif followers_only and me_user_id:
                from database.models.followers import Follower
                followers_subquery = select(Follower.follower_id).where(Follower.user_id == me_user_id)
                base_query = base_query.where(User.id.in_(followers_subquery))
            
            # Если ищем только среди подписок
            elif following_only and me_user_id:
                from database.models.followers import Follower
                following_subquery = select(Follower.user_id).where(Follower.follower_id == me_user_id)
                base_query = base_query.where(User.id.in_(following_subquery))
            
            result = await session.execute(
                base_query.offset(skip).limit(limit)
            )
            return result.scalars().all()

    @staticmethod
    async def get_users_by_role_with_relations(role_id: int):
        """Получить пользователей по роли с загрузкой отношений"""
        async with manager.get_async_session() as session:
            result = await session.execute(
                select(User)
                .where(User.role == role_id)
                .options(
                    joinedload(User.initiated_friendships),
                    joinedload(User.received_friendships)
                )
            )
            users = result.scalars().all()
            
            # Загружаем DynamicMapped отношения для каждого пользователя
            for user in users:
                # followers - кто подписан на этого пользователя
                followers_result = await session.execute(
                    select(Follower.follower_id).where(Follower.user_id == user.id)
                )
                user._followers_ids = [row[0] for row in followers_result.fetchall()]
                
                # following - на кого подписан этот пользователь
                following_result = await session.execute(
                    select(Follower.user_id).where(Follower.follower_id == user.id)
                )
                user._following_ids = [row[0] for row in following_result.fetchall()]
            
            return users

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
    
    @staticmethod
    async def change_password(user_id: int, old_password: str, new_password: str) -> User:
        """Изменить пароль пользователя с проверкой старого пароля."""
        async with manager.get_async_session() as session:
            try:
                result = await session.execute(select(User).where(User.id == user_id))
                user = result.scalars().first()
                if not user:
                    raise UserNotFoundError()
                
                # Проверяем старый пароль
                db_password_hash = getattr(user, "password_hash", None)
                if not db_password_hash or not bcrypt.checkpw(
                    old_password.encode("utf-8"), 
                    db_password_hash.encode("utf-8")
                ):
                    app_logger.warning_event("password_change_invalid_old", user_id=user_id)
                    raise InvalidOldPasswordError()
                
                # Хешируем новый пароль
                new_password_hash = UserManager._hash_password(new_password)
                user.password_hash = new_password_hash
                
                await session.commit()
                await session.refresh(user)
                
                app_logger.info_event("password_changed", user_id=user_id)
                return user
            except (UserNotFoundError, InvalidOldPasswordError):
                raise
            except Exception as e:
                await session.rollback()
                app_logger.exception(f"Ошибка при смене пароля пользователя {user_id}: {e}")
                raise DatabaseError("Ошибка при смене пароля")
    
    @staticmethod
    async def get_users_by_role(role_id: int) -> list[User]:
        """Получить всех пользователей с определенной ролью."""
        try:
            async with manager.get_async_session() as session:
                result = await session.execute(
                    select(User).where(User.role == role_id).order_by(User.login)
                )
                return list(result.scalars().all())
        except Exception as e:
            app_logger.exception(f"Ошибка при получении пользователей с ролью {role_id}: {e}")
            raise DatabaseError(f"Ошибка при получении пользователей с ролью {role_id}")
    
    @staticmethod
    async def get_role_statistics() -> dict[int, int]:
        """Получить статистику распределения ролей."""
        try:
            async with manager.get_async_session() as session:
                from sqlalchemy import func
                result = await session.execute(
                    select(User.role, func.count(User.id))
                    .group_by(User.role)
                    .order_by(User.role)
                )
                return {role_id: count for role_id, count in result.all()}
        except Exception as e:
            app_logger.exception(f"Ошибка при получении статистики ролей: {e}")
            raise DatabaseError("Ошибка при получении статистики ролей")
    
    @staticmethod
    async def update_user_role(user_id: int, new_role: int) -> User:
        """Обновить роль пользователя."""
        try:
            async with manager.get_async_session() as session:
                result = await session.execute(select(User).where(User.id == user_id))
                user = result.scalars().first()
                if not user:
                    raise UserNotFoundError()
                
                user.role = new_role
                await session.commit()
                await session.refresh(user)
                
                app_logger.info(f"Роль пользователя {user.login} (ID: {user_id}) изменена на {new_role}")
                return user
        except UserNotFoundError:
            raise
        except Exception as e:
            app_logger.exception(f"Ошибка при обновлении роли пользователя {user_id}: {e}")
            raise DatabaseError(f"Ошибка при обновлении роли пользователя")
    
    @staticmethod
    async def update_user_avatar(user_id: int, avatar_key: str) -> User:
        """Обновить аватар пользователя.
        
        Args:
            user_id: ID пользователя
            avatar_key: object_key аватара в S3 (например: "avatars/uuid.jpg")
            
        Returns:
            User: Обновленный пользователь
            
        Raises:
            UserNotFoundError: Пользователь не найден
            DatabaseError: Ошибка базы данных
            
        Example:
            >>> user = await UserManager.update_user_avatar(123, "avatars/new-avatar.jpg")
            >>> print(user.avatar_key)  # "avatars/new-avatar.jpg"
        """
        try:
            async with manager.get_async_session() as session:
                result = await session.execute(select(User).where(User.id == user_id))
                user = result.scalars().first()
                if not user:
                    raise UserNotFoundError()
                
                user.avatar_key = avatar_key
                await session.commit()
                await session.refresh(user)
                
                app_logger.info(f"Аватар пользователя {user.login} (ID: {user_id}) обновлен: {avatar_key}")
                return user
        except UserNotFoundError:
            raise
        except Exception as e:
            app_logger.exception(f"Ошибка при обновлении аватара пользователя {user_id}: {e}")
            raise DatabaseError(f"Ошибка при обновлении аватара пользователя")

