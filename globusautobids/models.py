"""SQLAlchemy models for keeping track of globus guest collections."""

from sqlalchemy import Column, ForeignKey, Integer, Table, Text
from sqlalchemy.orm import declarative_base, relationship
from sqlalchemy.dialects.postgresql import UUID

Base = declarative_base()


association_table = Table(
    "association",
    Base.metadata,
    Column("guest_collection_id", ForeignKey("guest_collection.id"), primary_key=True),
    Column("globus_user_id", ForeignKey("globus_user.id"), primary_key=True),
)


class GuestCollection(Base):
    __tablename__ = "guest_collection"

    id = Column(Integer, primary_key=True)
    study_id = Column(Integer, unique=True, nullable=False)
    globus_uuid = Column(UUID, unique=True, nullable=False)

    globus_users = relationship(
        "GlobusUser", secondary=association_table, backref="guest_collections"
    )


class GlobusUser(Base):
    __tablename__ = "globus_user"

    id = Column(Integer, primary_key=True)
    username = Column(Text, unique=True, nullable=False)
    guest_collection_id = Column(Integer, ForeignKey("guest_collection.id"))
