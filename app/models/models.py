from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import Column, Integer, String

Base = declarative_base()

class DiaryLog(Base):
    __tablename__ = "game_logs"

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(String)
    user_id = Column(String)
    timestamp = Column(String)
    ingame_datetime = Column(String)
    location = Column(String)
    action_type = Column(String)
    action_name = Column(String)
    detail = Column(String)
    with_ = Column("with", String)