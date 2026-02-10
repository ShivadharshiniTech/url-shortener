from sqlalchemy import Column, Integer, String, DateTime, Boolean
from sqlalchemy.sql import func
from api.database import Base

class Url(Base):
    __tablename__ = "urls"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    original_url = Column(String, nullable=False)
    custom_alias = Column(String, unique=True, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    is_active = Column(Boolean, default=True)
    click_count = Column(Integer, default=0)
    
    @property
    def short_code(self) -> str:
        """Generate short code from ID using Base62 encoding"""
        from api.utils import encode_id
        return encode_id(self.id)

class Click(Base):
    __tablename__ = "clicks"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    url_id = Column(Integer, nullable=False)  # Foreign key to urls.id
    ip_address = Column(String, nullable=True)
    user_agent = Column(String, nullable=True)
    referer = Column(String, nullable=True)
    clicked_at = Column(DateTime(timezone=True), server_default=func.now())