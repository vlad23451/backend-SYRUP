#TODO: Переделать модель на новый лад алхимии с mapped_collumn
from sqlalchemy import Column
from sqlalchemy import Integer
from sqlalchemy import String
from sqlalchemy import Text
from sqlalchemy import DateTime
from sqlalchemy import ForeignKey
from sqlalchemy import Boolean
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from database.config import Base

class MediaFile(Base):
    __tablename__ = "media_files"
    
    id = Column(Integer, primary_key=True, index=True)
    filename = Column(String(255), nullable=False)
    file_key = Column(String(500), nullable=False)
    file_type = Column(String(50), nullable=False)
    mime_type = Column(String(100), nullable=False)
    file_size = Column(Integer, nullable=False)
    folder = Column(String(50), nullable=False)
    
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    history_id = Column(Integer, ForeignKey("histories.id"), nullable=True)
    comment_id = Column(Integer, ForeignKey("comments.id"), nullable=True)
    
    is_public = Column(Boolean, default=False)
    description = Column(Text, nullable=True)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    
    user = relationship("User", back_populates="media_files")
    history = relationship("History", back_populates="media_files")
    comment = relationship("Comment", back_populates="media_files")
