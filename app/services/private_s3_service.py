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

class PrivateS3Service:
    """Сервис для работы с приватным S3 хранилищем для медиафайлов.
    
    Использует отдельный бакет для приватных медиафайлов (голосовые сообщения, видео, фото).
    """
    
    def __init__(self):
        """Инициализация приватного S3 клиента."""
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
            if getattr(settings, "private_s3_ca_bundle_path", None):
                verify_option = settings.private_s3_ca_bundle_path
            else:
                verify_option = bool(getattr(settings, "private_s3_verify_ssl", True))

            self.s3_client = boto3.client(
                's3',
                endpoint_url=settings.private_s3_endpoint_url,
                aws_access_key_id=settings.private_s3_access_key_id,
                aws_secret_access_key=settings.private_s3_secret_access_key,
                region_name=settings.private_s3_region,
                use_ssl=settings.private_s3_use_ssl,
                verify=verify_option,
                config=config
            )

            self.bucket_name = settings.private_s3_bucket_name
        except NoCredentialsError:
            app_logger.error("Private S3 credentials not found")
            raise S3ServiceUnavailableError("Не удалось подключиться к приватному хранилищу: отсутствуют учетные данные")
        except Exception as e:
            app_logger.error(f"Failed to initialize private S3 client: {e}")
            raise S3ServiceUnavailableError("Ошибка инициализации приватного S3 клиента")

    async def upload_file(self, file: bytes, filename: str, folder: str) -> str:
        """Загружает файл в приватный S3 и возвращает object_key.
        
        Args:
            file: Содержимое файла в виде байтов
            filename: Оригинальное имя файла (например: "voice.mp3")
            folder: Папка в бакете (например: "voice_messages")
            
        Returns:
            str: object_key файла в формате "folder/uuid.extension"
            
        Raises:
            S3UploadError: Ошибка при загрузке файла
            S3ServiceUnavailableError: S3 сервис недоступен
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
            
            app_logger.info(f"Private file uploaded successfully: {object_key}")
            return object_key
            
        except EndpointConnectionError:
            app_logger.error("Private S3 endpoint connection error")
            raise S3ServiceUnavailableError("Не удалось подключиться к приватному хранилищу")
        except ClientError as e:
            error_code = e.response['Error']['Code']
            app_logger.error(f"Private S3 ClientError during upload: {error_code}")
            if error_code == 'NoSuchBucket':
                raise S3ServiceUnavailableError("Приватный бакет не найден")
            else:
                raise S3UploadError(f"Ошибка загрузки файла в приватное хранилище: {error_code}")
        except Exception as e:
            app_logger.error(f"Unexpected error during private file upload: {e}")
            raise S3UploadError("Неожиданная ошибка при загрузке файла в приватное хранилище")

    async def generate_presigned_url(self, object_key: str, expires_in: int = 3600) -> str:
        """Генерирует временную ссылку на объект в приватном S3.
        
        Args:
            object_key: Ключ объекта в S3 (например: "voice_messages/uuid.mp3")
            expires_in: Время жизни ссылки в секундах (по умолчанию 1 час)
            
        Returns:
            str: Временная ссылка на объект
            
        Raises:
            S3ObjectNotFoundError: Объект не найден
            S3ServiceUnavailableError: S3 сервис недоступен
        """
        try:
            # Проверяем, существует ли объект
            try:
                self.s3_client.head_object(Bucket=self.bucket_name, Key=object_key)
            except ClientError as e:
                if e.response['Error']['Code'] == '404':
                    app_logger.warning(f"Private object not found: {object_key}")
                    raise S3ObjectNotFoundError("Файл не найден в приватном хранилище")
                else:
                    raise
            
            # Генерируем presigned URL
            url = self.s3_client.generate_presigned_url(
                'get_object',
                Params={'Bucket': self.bucket_name, 'Key': object_key},
                ExpiresIn=expires_in
            )
            
            app_logger.info(f"Generated presigned URL for private file: {object_key}")
            return url
            
        except EndpointConnectionError:
            app_logger.error("Private S3 endpoint connection error")
            raise S3ServiceUnavailableError("Не удалось подключиться к приватному хранилищу")
        except S3ObjectNotFoundError:
            raise
        except ClientError as e:
            error_code = e.response['Error']['Code']
            app_logger.error(f"Private S3 ClientError during presigned URL generation: {error_code}")
            raise S3ServiceUnavailableError(f"Ошибка генерации ссылки для приватного файла: {error_code}")
        except Exception as e:
            app_logger.error(f"Unexpected error during private presigned URL generation: {e}")
            raise S3ServiceUnavailableError("Неожиданная ошибка при генерации ссылки для приватного файла")

    async def delete_file(self, object_key: str) -> bool | None:
        """Удаляет файл из приватного S3.
        
        Args:
            object_key: Ключ объекта в S3 (например: "voice_messages/uuid.mp3")
            
        Returns:
            bool: True если файл удален, None если файл не существовал
            
        Raises:
            S3ServiceUnavailableError: S3 сервис недоступен
        """
        try:
            # Проверяем, существует ли объект
            try:
                self.s3_client.head_object(Bucket=self.bucket_name, Key=object_key)
            except ClientError as e:
                if e.response['Error']['Code'] == '404':
                    app_logger.info(f"Private object not found during deletion: {object_key}")
                    return None
                else:
                    raise
            
            # Удаляем объект
            self.s3_client.delete_object(Bucket=self.bucket_name, Key=object_key)
            
            app_logger.info(f"Private file deleted successfully: {object_key}")
            return True
            
        except EndpointConnectionError:
            app_logger.error("Private S3 endpoint connection error")
            raise S3ServiceUnavailableError("Не удалось подключиться к приватному хранилищу")
        except ClientError as e:
            error_code = e.response['Error']['Code']
            app_logger.error(f"Private S3 ClientError during deletion: {error_code}")
            raise S3ServiceUnavailableError(f"Ошибка удаления файла из приватного хранилища: {error_code}")
        except Exception as e:
            app_logger.error(f"Unexpected error during private file deletion: {e}")
            raise S3ServiceUnavailableError("Неожиданная ошибка при удалении файла из приватного хранилища")

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
            'mov': 'video/quicktime',
            'avi': 'video/x-msvideo',
            'mp3': 'audio/mpeg',
            'wav': 'audio/wav',
            'aac': 'audio/aac',
            'm4a': 'audio/mp4',
            'pdf': 'application/pdf',
            'txt': 'text/plain'
        }
        
        return content_types.get(extension, 'application/octet-stream')
