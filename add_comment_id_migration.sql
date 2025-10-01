-- SQLite миграция для добавления поля comment_id в таблицу media_files
-- Выполните этот скрипт в вашей SQLite базе данных

-- Добавляем поле comment_id (ID комментария, к которому прикреплен файл)
ALTER TABLE media_files ADD COLUMN comment_id INTEGER;

-- Создаем внешний ключ для связи с таблицей comments
-- В SQLite внешние ключи нужно создавать отдельно
-- (если у вас включена поддержка внешних ключей)

-- Создаем индекс для быстрого поиска файлов по комментарию
CREATE INDEX idx_media_files_comment_id ON media_files(comment_id);

-- Проверяем структуру таблицы
PRAGMA table_info(media_files);
