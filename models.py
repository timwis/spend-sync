from sqlalchemy import Column, ForeignKey, Integer, String
from sqlalchemy.orm import declarative_base, relationship
from sqlalchemy.types import TIMESTAMP

Base = declarative_base()

class User(Base):
    __tablename__ = "auth.users"

    id = Column(Integer, primary_key=True)

    connections = relationship("Connection", back_populates="user")
    job_definitions = relationship("JobDefinition", back_populates="user")

    def __repr__(self):
        return f"User(id={self.id!r})"

class Connection(Base):
    __tablename__ = "decrypted_connections"

    id = Column(Integer, primary_key=True)
    created_at = Column(TIMESTAMP, nullable=False)
    user_id = Column(Integer, ForeignKey("auth.users.id"), nullable=False)
    access_token = Column(String, nullable=False)
    decrypted_access_token = Column(String)
    expires_at = Column(TIMESTAMP)
    refresh_token = Column(String, nullable=False)
    decrypted_refresh_token = Column(String)
    # key_id

    user = relationship("User", back_populates="connections")
    accounts = relationship("Account", back_populates="connection")
    
    def __repr__(self):
        return f"Connection(id={self.id})"

class Account(Base):
    __tablename__ = "accounts"

    id = Column(Integer, primary_key=True)
    created_at = Column(TIMESTAMP, nullable=False)
    account_type = Column(String, nullable=False)
    truelayer_account_id = Column(String, nullable=False)
    truelayer_display_name = Column(String, nullable=False)
    connection_id = Column(Integer, ForeignKey("decrypted_connections.id"), nullable=False)
     
    connection = relationship("Connection", back_populates="accounts")
    job_definitions = relationship("JobDefinition", back_populates="card_account")

    def __repr__(self):
        return f"Account(id={self.id!r}, account_type={self.account_type!r})"

class JobDefinition(Base):
    __tablename__ = "job_definitions"

    id = Column(Integer, primary_key=True)
    created_at = Column(TIMESTAMP, nullable=False)
    user_id = Column(Integer, ForeignKey("auth.users.id"), nullable=False)
    card_account_id = Column(Integer, ForeignKey("accounts.id"), nullable=False)
    last_synced_at = Column(TIMESTAMP)

    user = relationship("User", back_populates="job_definitions")
    card_account = relationship("Account", back_populates="job_definitions")

    def __repr__(self):
        return f"JobDefinition(id={self.id!r})"
