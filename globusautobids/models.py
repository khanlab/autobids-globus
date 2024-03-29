"""SQLAlchemy models for keeping track of globus guest collections."""
from __future__ import annotations

from enum import Enum

from sqlalchemy import Column
from sqlalchemy import Enum as SqlEnum
from sqlalchemy import ForeignKey, Integer, Table, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()


class DatasetType(Enum):
    """Enum to describe the possible dataset types."""

    SOURCE_DATA = 1
    RAW_DATA = 2
    DERIVED_DATA = 3

    @classmethod
    def from_bids_str(cls, bids_str: str) -> DatasetType:
        """Get dataset type

        Parameters
        ----------
        bids_str
            One of sourcedata, rawdata, or deriveddata to indicate dataset type

        Returns
        -------
        int
            Integer representation of dataset type
        """
        map = {
            "sourcedata": DatasetType.SOURCE_DATA,
            "rawdata": DatasetType.RAW_DATA,
            "deriveddata": DatasetType.DERIVED_DATA,
        }
        return map[bids_str]


association_table = Table(
    "association",
    Base.metadata,  # pyright: ignore
    Column("guest_collection_id", ForeignKey("guest_collection.id"), primary_key=True),
    Column("globus_user_id", ForeignKey("globus_user.id"), primary_key=True),
)


class GuestCollection(Base):
    __tablename__ = "guest_collection"
    __table_args__ = (
        UniqueConstraint(
            "study_id", "dataset_type", name="uq_guest_collection_study_id_dataset_type"
        ),
    )

    id = Column(Integer, primary_key=True)
    study_id = Column(Integer, unique=False, nullable=False)
    dataset_type = Column(SqlEnum(DatasetType), unique=False, nullable=False)
    globus_uuid = Column(UUID, unique=True, nullable=False)

    globus_users = relationship(
        "GlobusUser", secondary=association_table, backref="guest_collections"
    )


class GlobusUser(Base):
    __tablename__ = "globus_user"

    id = Column(Integer, primary_key=True)
    username = Column(Text, unique=True, nullable=False)
    guest_collection_id = Column(Integer, ForeignKey("guest_collection.id"))
