from datetime import datetime, timezone
from typing import Optional
from uuid import UUID, uuid4
from enum import Enum
from sqlmodel import Column, DateTime, Field, JSON, Relationship, SQLModel


class Status(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    REVIEW = "review"
    FAILED = "failed"


class FormSetup(SQLModel, table=True):
    __tablename__ = "form_setups" # type: ignore

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    name: str
    original_filename: str
    pdf_url: str

    summary: str | None = None
    context: str | None = None
    styling: dict | None = Field(default=None, sa_column=Column(JSON))

    status: str = Field(default=Status.PENDING.value, index=True)

    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(DateTime(timezone=True), nullable=False),
    )
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(DateTime(timezone=True), nullable=False),
    )

    images: list["FormSetupImage"] = Relationship(back_populates="setup")
    sections: list["FormSetupSection"] = Relationship(back_populates="setup")
    job: Optional["ProcessingJob"] = Relationship(back_populates="setup")


class ProcessingJob(SQLModel, table=True):
    __tablename__ = "processing_jobs" # type: ignore

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    setup_id: UUID = Field(foreign_key="form_setups.id", index=True)

    status: str = Field(default=Status.PENDING.value, index=True)
    progress: int = Field(default=0)
    current_step: str | None = None
    error: str | None = None

    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(DateTime(timezone=True), nullable=False),
    )
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(DateTime(timezone=True), nullable=False),
    )

    setup: FormSetup = Relationship(back_populates="job")


class FormSetupImage(SQLModel, table=True):
    __tablename__ = "form_setup_images" # type: ignore

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    setup_id: UUID = Field(foreign_key="form_setups.id", index=True)

    page_number: int
    image_url: str

    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(DateTime(timezone=True), nullable=False),
    )

    setup: FormSetup = Relationship(back_populates="images")


class FormSetupSection(SQLModel, table=True):
    __tablename__ = "form_setup_sections" # type: ignore

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    setup_id: UUID = Field(foreign_key="form_setups.id", index=True)

    section_number: int = Field(index=True)
    name: str
    description: str | None = None
    page_start: int
    page_end: int

    fields: list | None = Field(default=None, sa_column=Column(JSON))

    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(DateTime(timezone=True), nullable=False),
    )
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(DateTime(timezone=True), nullable=False),
    )

    setup: FormSetup = Relationship(back_populates="sections")