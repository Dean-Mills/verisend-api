from datetime import datetime, timezone
from enum import Enum
from typing import Optional
from uuid import UUID, uuid4
from sqlmodel import Column, DateTime, Field, JSON, Relationship, SQLModel

# =============================================================================
# Enums
# =============================================================================

class SetupStatus(str, Enum):
    """Status of the form setup process"""
    UPLOAD = "upload"           # Document uploaded, OCR complete
    SECTIONS = "sections"       # Sections detected, ready for review
    REVIEW = "review"           # User reviewing/editing sections
    CONVERT = "convert"         # Sections confirmed, ready for conversion
    MAPPING = "mapping"         # Fields converted, ready for standard field mapping
    BUILDER = "builder"         # Mapping complete, in form builder
    COMPLETED = "completed"     # Form finalized and created

class SectionStatus(str, Enum):
    """Status of a single section in the review process"""
    PENDING = "pending"         # Section detected, not yet extracted
    EXTRACTING = "extracting"   # Extraction in progress
    REVIEW = "review"           # Fields extracted, user reviewing
    CONFIRMED = "confirmed"     # User confirmed, ready for aggregation

# =============================================================================
# Organization & User
# =============================================================================

class Organization(SQLModel, table=True):
    """A tenant/company that owns forms and has users"""
    __tablename__ = "organizations" # type: ignore

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    name: str = Field(index=True)
    slug: str = Field(unique=True, index=True)
    is_active: bool = Field(default=True)

    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(DateTime(timezone=True), nullable=False),
    )
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(DateTime(timezone=True), nullable=False),
    )

    # Relationships
    users: list["User"] = Relationship(back_populates="organization")
    forms: list["Form"] = Relationship(back_populates="organization")

class User(SQLModel, table=True):
    """User synced from Keycloak on first login"""
    __tablename__ = "users" # type: ignore

    id: str = Field(primary_key=True)  # Keycloak 'sub' claim
    email: str = Field(index=True)
    name: str | None = None
    role: str = Field(default="user", index=True)  # super_admin, admin, publisher, user

    organization_id: UUID | None = Field(
        default=None,
        foreign_key="organizations.id",
        index=True,
    )
    is_active: bool = Field(default=True)

    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(DateTime(timezone=True), nullable=False),
    )
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(DateTime(timezone=True), nullable=False),
    )

    # Relationships
    organization: Optional["Organization"] = Relationship(back_populates="users")

# =============================================================================
# Forms
# =============================================================================

class Form(SQLModel, table=True):
    """A form template created by a publisher"""
    __tablename__ = "forms" # type: ignore

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    name: str
    description: str | None = None
    json_schema: dict = Field(sa_column=Column(JSON))

    organization_id: UUID = Field(foreign_key="organizations.id", index=True)
    created_by: str = Field(foreign_key="users.id", index=True)
    is_deleted: bool = Field(default=False, index=True)

    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(DateTime(timezone=True), nullable=False),
    )
    updated_at: datetime | None = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(DateTime(timezone=True), nullable=True),
    )

    # Relationships
    organization: Organization = Relationship(back_populates="forms")
    assignments: list["FormAssignment"] = Relationship(back_populates="form")

class FormAssignment(SQLModel, table=True):
    """Links forms to users who need to fill them"""
    __tablename__ = "form_assignments" # type: ignore

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    form_id: UUID = Field(foreign_key="forms.id", index=True, ondelete="CASCADE")
    user_id: str = Field(foreign_key="users.id", index=True, ondelete="CASCADE")
    assigned_by: str = Field(foreign_key="users.id", index=True)
    status: str = Field(default="pending", index=True)  # pending, in_progress, completed

    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(DateTime(timezone=True), nullable=False),
    )
    completed_at: datetime | None = Field(
        default=None,
        sa_column=Column(DateTime(timezone=True), nullable=True),
    )

    # Relationships
    form: Form = Relationship(back_populates="assignments")

# =============================================================================
# Form Setup (PDF to Digital Form Pipeline)
# =============================================================================

class FormSetup(SQLModel, table=True):
    """Tracks the extraction and setup process for a form"""
    __tablename__ = "form_setups" # type: ignore

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    user_id: str = Field(foreign_key="users.id", index=True)
    organization_id: UUID = Field(foreign_key="organizations.id", index=True)

    # Document info
    original_filename: str
    original_document_url: str | None = None
    markdown: str | None = None  # Full OCR markdown

    # Context (from context_agent)
    form_title: str | None = None
    form_description: str | None = None
    user_comment: str | None = None

    # Pipeline status
    status: str = Field(default=SetupStatus.UPLOAD.value, index=True)

    # Post-section aggregation (after all sections confirmed)
    raw_fields: list | None = Field(default=None, sa_column=Column(JSON))

    # Conversion output
    surveyjs_elements: list | None = Field(default=None, sa_column=Column(JSON))

    # Final schema (after grouping)
    final_form_schema: dict | None = Field(default=None, sa_column=Column(JSON))

    # Link to created form
    form_id: UUID | None = Field(default=None, foreign_key="forms.id")

    is_deleted: bool = Field(default=False, index=True)

    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(DateTime(timezone=True), nullable=False),
    )
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(DateTime(timezone=True), nullable=False),
    )

    # Relationships
    images: list["FormSetupImage"] = Relationship(back_populates="setup")
    sections: list["FormSetupSection"] = Relationship(back_populates="setup")

class FormSetupImage(SQLModel, table=True):
    """Stores page images extracted from documents"""
    __tablename__ = "form_setup_images" # type: ignore

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    setup_id: UUID = Field(foreign_key="form_setups.id", index=True, ondelete="CASCADE")

    page_number: int
    image_url: str
    markdown: str | None = None

    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(DateTime(timezone=True), nullable=False),
    )

    # Relationships
    setup: FormSetup = Relationship(back_populates="images")

class FormSetupSection(SQLModel, table=True):
    """A visual section of the form for incremental review"""
    __tablename__ = "form_setup_sections" # type: ignore

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    setup_id: UUID = Field(foreign_key="form_setups.id", index=True, ondelete="CASCADE")

    # Section identification
    section_number: int = Field(index=True)  # Order in form (1, 2, 3...)
    name: str  # e.g., "Personal Information", "Employment Details"
    description: str | None = None  # Brief description of what this section contains

    # Page coverage (inclusive)
    page_start: int  # First page this section appears on
    page_end: int    # Last page this section appears on

    # Pipeline status
    status: str = Field(default=SectionStatus.PENDING.value, index=True)

    # Extracted fields for THIS section only
    raw_fields: list | None = Field(default=None, sa_column=Column(JSON))

    # Conversation history for chat-based refinement
    # Format: [{"role": "assistant"|"user", "content": "..."}, ...]
    messages: list | None = Field(default=None, sa_column=Column(JSON))

    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(DateTime(timezone=True), nullable=False),
    )
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(DateTime(timezone=True), nullable=False),
    )

    # Relationships
    setup: FormSetup = Relationship(back_populates="sections")


# =============================================================================
# Responses & User Data
# =============================================================================

class Response(SQLModel, table=True):
    """A user's submission of a filled form"""
    __tablename__ = "responses" # type: ignore

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    form_id: UUID = Field(foreign_key="forms.id", index=True, ondelete="CASCADE")
    user_id: str = Field(foreign_key="users.id", index=True)
    assignment_id: UUID | None = Field(
        default=None,
        foreign_key="form_assignments.id",
        index=True,
    )

    response_data: dict = Field(sa_column=Column(JSON))

    submitted_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(DateTime(timezone=True), nullable=False),
    )

class UserStandardFieldValue(SQLModel, table=True):
    """User's saved values for auto-fill standard fields"""
    __tablename__ = "user_standard_field_values" # type: ignore

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    user_id: str = Field(foreign_key="users.id", index=True)
    standard_field_id: UUID = Field(index=True)
    value: str

    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(DateTime(timezone=True), nullable=False),
    )
    updated_at: datetime | None = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(DateTime(timezone=True), nullable=True),
    )