import uuid
import boto3

from botocore.config import Config
from botocore.exceptions import ClientError
from botocore.exceptions import NoCredentialsError
from botocore.exceptions import EndpointConnectionError

from core.config import settings
from core.logger import app_logger

from exceptions.s3 import S3ObjectNotFoundError
from exceptions.s3 import S3ServiceUnavailableError
from exceptions.s3 import S3UploadError

class S3Service:
    """Сервис для работы с S3 хранилищем.
    
    Особенности конфигурации:
    - Принудительное отключение всех прокси (proxies={})
    - Настройка повторных попыток соединения
    - Увеличенный пул соединений для лучшей производительности
    """
    
    def __init__(self):
        """Инициализация S3 клиента."""
        try:
            config = Config(
                proxies={},  # Принудительно отключаем все прокси
                retries={
                    'max_attempts': 3,
                    'mode': 'standard'
                },
                max_pool_connections=50,
                signature_version='s3v4'
            )

            # Настройка verify: путь к CA-бандлу приоритетнее, затем bool-флаг
            verify_option = True
            if getattr(settings, "s3_ca_bundle_path", None):
                verify_option = settings.s3_ca_bundle_path
            else:
                verify_option = bool(getattr(settings, "s3_verify_ssl", True))

            self.s3_client = boto3.client(
                's3',
                endpoint_url=settings.s3_endpoint_url,
                aws_access_key_id=settings.private_s3_access_key_id,
                aws_secret_access_key=settings.private_s3_secret_access_key,
                region_name=settings.s3_region,
                use_ssl=settings.s3_use_ssl,
                verify=verify_option,
                config=config
            )

            self.bucket_name = settings.s3_bucket_name
        except NoCredentialsError:
            app_logger.error("S3 credentials not found")
            raise S3ServiceUnavailableError("Не удалось подключиться к хранилищу: отсутствуют учетные данные")
        except Exception as e:
            app_logger.error(f"Failed to initialize S3 client: {e}")
            raise S3ServiceUnavailableError("Ошибка инициализации S3 клиента")

    async def upload_file(self, file: bytes, filename: str, folder: str) -> str:
        """Загружает файл в S3 и возвращает object_key.
        
        Args:
            file: Содержимое файла в виде байтов
            filename: Оригинальное имя файла (например: "avatar.jpg")
            folder: Папка в бакете (например: "avatars")
            
        Returns:
            str: object_key файла в формате "folder/uuid.extension"
            
        Raises:
            S3UploadError: Ошибка при загрузке файла
            S3ServiceUnavailableError: S3 сервис недоступен
            
        Example:
            >>> service = S3Service()
            >>> with open('photo.jpg', 'rb') as f:
            ...     data = f.read()
            >>> key = await service.upload_file(data, 'photo.jpg', 'avatars')
            >>> print(key)  # "avatars/cbff3388-5c25-45c4-b6ca-9fa4f372aca1.jpg"
        """
        try:
            # Генерируем уникальное имя файла
            file_extension = filename.split('.')[-1] if '.' in filename else ''
            unique_filename = f"{uuid.uuid4()}"
            if file_extension:
                unique_filename += f".{file_extension}"
            
            # Формируем object_key
            object_key = f"{folder.rstrip('/')}/{unique_filename}"
            
            # Загружаем файл
            self.s3_client.put_object(
                Bucket=self.bucket_name,
                Key=object_key,
                Body=file,
                ContentType=self._get_content_type(filename)
            )
            
            app_logger.info(f"File uploaded successfully: {object_key}")
            return object_key
            
        except EndpointConnectionError:
            app_logger.error("S3 endpoint connection error")
            raise S3ServiceUnavailableError("Не удалось подключиться к хранилищу")
        except ClientError as e:
            error_code = e.response['Error']['Code']
            app_logger.error(f"S3 ClientError during upload: {error_code}")
            if error_code == 'NoSuchBucket':
                raise S3ServiceUnavailableError("Бакет не найден")
            else:
                raise S3UploadError(f"Ошибка загрузки файла: {error_code}")
        except Exception as e:
            app_logger.error(f"Unexpected error during file upload: {e}")
            raise S3UploadError("Неожиданная ошибка при загрузке файла")

    async def generate_presigned_url(self, object_key: str, expires_in: int = 3600) -> str:
        """Генерирует временную ссылку на объект в S3.
        
        Args:
            object_key: Ключ объекта в S3 (например: "avatars/uuid.jpg")
            expires_in: Время жизни ссылки в секундах (по умолчанию 1 час)
            
        Returns:
            str: Временная ссылка на объект
            
        Raises:
            S3ObjectNotFoundError: Объект не найден
            S3ServiceUnavailableError: S3 сервис недоступен
            
        Example:
            >>> service = S3Service()
            >>> url = await service.generate_presigned_url("avatars/file.jpg")
            >>> print(url)  # "https://s3.ru-7.storage.selcloud.ru/bucket/avatars/file.jpg?..."
        """
        try:
            # Проверяем, существует ли объект
            try:
                self.s3_client.head_object(Bucket=self.bucket_name, Key=object_key)
            except ClientError as e:
                if e.response['Error']['Code'] == '404':
                    app_logger.warning(f"Object not found: {object_key}")
                    raise S3ObjectNotFoundError("Файл не найден")
                else:
                    raise
            
            # Генерируем presigned URL
            url = self.s3_client.generate_presigned_url(
                'get_object',
                Params={'Bucket': self.bucket_name, 'Key': object_key},
                ExpiresIn=expires_in
            )
            
            app_logger.info(f"Generated presigned URL for: {object_key}")
            return url
            
        except EndpointConnectionError:
            app_logger.error("S3 endpoint connection error")
            raise S3ServiceUnavailableError("Не удалось подключиться к хранилищу")
        except S3ObjectNotFoundError:
            raise
        except ClientError as e:
            error_code = e.response['Error']['Code']
            app_logger.error(f"S3 ClientError during presigned URL generation: {error_code}")
            raise S3ServiceUnavailableError(f"Ошибка генерации ссылки: {error_code}")
        except Exception as e:
            app_logger.error(f"Unexpected error during presigned URL generation: {e}")
            raise S3ServiceUnavailableError("Неожиданная ошибка при генерации ссылки")

    async def delete_file(self, object_key: str) -> bool | None:
        """Удаляет файл из S3.
        
        Args:
            object_key: Ключ объекта в S3 (например: "avatars/uuid.jpg")
            
        Returns:
            bool: True если файл удален, None если файл не существовал
            
        Raises:
            S3ServiceUnavailableError: S3 сервис недоступен
            
        Example:
            >>> service = S3Service()
            >>> result = await service.delete_file("avatars/old-file.jpg")
            >>> print(result)  # True или None
        """
        try:
            # Проверяем, существует ли объект
            try:
                self.s3_client.head_object(Bucket=self.bucket_name, Key=object_key)
            except ClientError as e:
                if e.response['Error']['Code'] == '404':
                    app_logger.info(f"Object not found during deletion: {object_key}")
                    return None
                else:
                    raise
            
            # Удаляем объект
            self.s3_client.delete_object(Bucket=self.bucket_name, Key=object_key)
            
            app_logger.info(f"File deleted successfully: {object_key}")
            return True
            
        except EndpointConnectionError:
            app_logger.error("S3 endpoint connection error")
            raise S3ServiceUnavailableError("Не удалось подключиться к хранилищу")
        except ClientError as e:
            error_code = e.response['Error']['Code']
            app_logger.error(f"S3 ClientError during deletion: {error_code}")
            raise S3ServiceUnavailableError(f"Ошибка удаления файла: {error_code}")
        except Exception as e:
            app_logger.error(f"Unexpected error during file deletion: {e}")
            raise S3ServiceUnavailableError("Неожиданная ошибка при удалении файла")

    def _get_content_type(self, filename: str) -> str:
        """Определяет Content-Type по расширению файла."""
        extension = filename.lower().split('.')[-1] if '.' in filename else ''
        
        content_types = {
            'jpg': 'image/jpeg',
            'jpeg': 'image/jpeg', 
            'png': 'image/png',
            'gif': 'image/gif',
            'webp': 'image/webp',
            'mp4': 'video/mp4',
            'webm': 'video/webm',
            'ogg': 'video/ogg',
            'mp3': 'audio/mpeg',
            'wav': 'audio/wav',
            'pdf': 'application/pdf',
            'txt': 'text/plain'
        }
        
        return content_types.get(extension, 'application/octet-stream')
