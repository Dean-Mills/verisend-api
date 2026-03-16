import logging
from uuid import UUID, uuid4
from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException, UploadFile, File, status
from typing import Literal

from pydantic import BaseModel
from sqlmodel import select

from verisend.utils.blob_storage import BlobStorageContainer
from verisend.utils.db import AsyncSession
from verisend.models.db_models import FormSetup, FormSetupSection, ProcessingJob, Status
from verisend.agents.summarise_agent import summarise_form
from verisend.workers.tasks import extract_form

logger = logging.getLogger(__name__)

TAGS = [
    {
        "name": "Setups",
        "description": "Endpoints for managing form setups",
    },
]

router = APIRouter(prefix="/setups", tags=["setups"])


# =============================================================================
# Request / Response models
# =============================================================================

class UploadResponse(BaseModel):
    setup_id: UUID
    pdf_url: str
    name: str
    summary: str


class ConfirmRequest(BaseModel):
    name: str
    summary: str | None = None
    context: str | None = None


class ConfirmResponse(BaseModel):
    setup_id: UUID
    job_id: UUID


class JobStatusResponse(BaseModel):
    setup_id: UUID
    job_id: UUID
    status: str
    progress: int
    current_step: str | None


class FieldResponse(BaseModel):
    label: str
    field_type: str
    required: bool
    placeholder: str | None
    help_text: str | None
    options: list[str] | None
    standard_field_key: str | None
    standard_field_reason: str | None


class SectionResponse(BaseModel):
    id: UUID
    section_number: int
    name: str
    description: str | None
    page_start: int
    page_end: int
    fields: list[FieldResponse]


class SetupSectionsResponse(BaseModel):
    setup_id: UUID
    name: str
    status: str
    sections: list[SectionResponse]


class FieldInput(BaseModel):
    label: str
    field_type: str
    required: bool = False
    placeholder: str | None = None
    help_text: str | None = None
    options: list[str] | None = None
    standard_field_key: str | None = None
    standard_field_reason: str | None = None


class SectionInput(BaseModel):
    id: UUID | None = None
    section_number: int
    name: str
    description: str | None = None
    page_start: int
    page_end: int
    fields: list[FieldInput]


class UpdateSectionsRequest(BaseModel):
    sections: list[SectionInput]


class UpdateSectionsResponse(BaseModel):
    sections: list[SectionResponse]


class StylingRequest(BaseModel):
    primary_color: str
    accent_color: str
    background_color: str
    surface_color: str
    text_color: str
    label_color: str
    border_color: str
    error_color: str
    font_family: str
    heading_size: Literal["sm", "md", "lg"]
    border_radius: Literal["none", "sm", "md", "lg", "full"]
    spacing: Literal["compact", "comfortable", "spacious"]
    button_style: Literal["filled", "outlined"]
    logo_url: str | None = None


class StylingResponse(StylingRequest):
    pass


# =============================================================================
# Endpoints
# =============================================================================

@router.post("/upload", response_model=UploadResponse, status_code=status.HTTP_201_CREATED)
async def upload(
    file: UploadFile = File(...),
    container: BlobStorageContainer = ...,
    session: AsyncSession = ...,
):
    setup_id = uuid4()
    now = datetime.now(timezone.utc)

    # Upload to blob first
    blob_path = f"setups/{setup_id}/original/{file.filename}"
    blob_client = container.get_blob_client(blob_path)
    contents = await file.read()
    blob_client.upload_blob(contents, overwrite=True)
    pdf_url = blob_client.url

    # Summarise while we have the URL
    result = await summarise_form(pdf_url)

    setup = FormSetup(
        id=setup_id,
        name=result.name,
        original_filename=file.filename or "",
        pdf_url=pdf_url,
        summary=result.summary,
        status=Status.PENDING.value,
        created_at=now,
        updated_at=now,
    )
    session.add(setup)
    await session.commit()

    return UploadResponse(
        setup_id=setup_id,
        pdf_url=pdf_url,
        name=result.name,
        summary=result.summary,
    )


@router.post("/{setup_id}/confirm", response_model=ConfirmResponse)
async def confirm(
    setup_id: UUID,
    body: ConfirmRequest,
    session: AsyncSession,
):
    setup = await session.get(FormSetup, setup_id)
    if not setup:
        raise HTTPException(status_code=404, detail="Setup not found")

    now = datetime.now(timezone.utc)
    job_id = uuid4()

    pdf_url = setup.pdf_url

    setup.name = body.name
    setup.summary = body.summary
    setup.context = body.context
    setup.status = Status.PROCESSING.value
    setup.updated_at = now

    job = ProcessingJob(
        id=job_id,
        setup_id=setup_id,
        status=Status.PENDING.value,
        progress=0,
        created_at=now,
        updated_at=now,
    )
    session.add(setup)
    session.add(job)
    await session.commit()

    extract_form.delay(str(job_id), str(setup_id), pdf_url, body.summary, body.context)

    return ConfirmResponse(setup_id=setup_id, job_id=job_id)


@router.get("/{setup_id}/status", response_model=JobStatusResponse)
async def get_status(
    setup_id: UUID,
    session: AsyncSession,
):
    statement = select(ProcessingJob).where(ProcessingJob.setup_id == setup_id)
    result = await session.exec(statement)
    job = result.first()

    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    job_id = job.id
    job_status = job.status
    job_progress = job.progress
    job_step = job.current_step

    return JobStatusResponse(
        setup_id=setup_id,
        job_id=job_id,
        status=job_status,
        progress=job_progress,
        current_step=job_step,
    )


@router.get("/{setup_id}/sections", response_model=SetupSectionsResponse)
async def get_sections(
    setup_id: UUID,
    session: AsyncSession,
):
    setup = await session.get(FormSetup, setup_id)
    if not setup:
        raise HTTPException(status_code=404, detail="Setup not found")

    setup_name = setup.name
    setup_status = setup.status

    statement = (
        select(FormSetupSection)
        .where(FormSetupSection.setup_id == setup_id)
        .order_by(FormSetupSection.section_number)
    )
    result = await session.exec(statement)
    sections = result.all()

    section_responses = []
    for s in sections:
        raw_fields = s.fields or []
        fields = [
            FieldResponse(
                label=f.get("label", ""),
                field_type=f.get("field_type", "short_text"),
                required=f.get("required", False),
                placeholder=f.get("placeholder"),
                help_text=f.get("help_text"),
                options=f.get("options"),
                standard_field_key=f.get("standard_field_key"),
                standard_field_reason=f.get("standard_field_reason"),
            )
            for f in raw_fields
        ]
        section_responses.append(
            SectionResponse(
                id=s.id,
                section_number=s.section_number,
                name=s.name,
                description=s.description,
                page_start=s.page_start,
                page_end=s.page_end,
                fields=fields,
            )
        )

    return SetupSectionsResponse(
        setup_id=setup_id,
        name=setup_name,
        status=setup_status,
        sections=section_responses,
    )


@router.put("/{setup_id}/sections", response_model=UpdateSectionsResponse)
async def update_sections(
    setup_id: UUID,
    body: UpdateSectionsRequest,
    session: AsyncSession,
):
    setup = await session.get(FormSetup, setup_id)
    if not setup:
        raise HTTPException(status_code=404, detail="Setup not found")

    now = datetime.now(timezone.utc)

    # Delete existing sections for this setup
    existing = await session.exec(
        select(FormSetupSection).where(FormSetupSection.setup_id == setup_id)
    )
    for old in existing.all():
        await session.delete(old)

    # Build new sections and capture response data before commit
    section_responses: list[SectionResponse] = []
    for s in body.sections:
        section_id = s.id or uuid4()
        field_dicts = [f.model_dump() for f in s.fields]

        section = FormSetupSection(
            id=section_id,
            setup_id=setup_id,
            section_number=s.section_number,
            name=s.name,
            description=s.description,
            page_start=s.page_start,
            page_end=s.page_end,
            fields=field_dicts,
            created_at=now,
            updated_at=now,
        )
        session.add(section)

        section_responses.append(
            SectionResponse(
                id=section_id,
                section_number=s.section_number,
                name=s.name,
                description=s.description,
                page_start=s.page_start,
                page_end=s.page_end,
                fields=[FieldResponse(**f) for f in field_dicts],
            )
        )

    setup.updated_at = now
    session.add(setup)
    await session.commit()

    return UpdateSectionsResponse(sections=section_responses)


@router.put("/{setup_id}/styling", response_model=StylingResponse)
async def update_styling(
    setup_id: UUID,
    body: StylingRequest,
    session: AsyncSession,
):
    setup = await session.get(FormSetup, setup_id)
    if not setup:
        raise HTTPException(status_code=404, detail="Setup not found")

    setup.styling = body.model_dump()
    setup.updated_at = datetime.now(timezone.utc)
    session.add(setup)
    await session.commit()

    return body


@router.get("/{setup_id}/styling", response_model=StylingResponse)
async def get_styling(
    setup_id: UUID,
    session: AsyncSession,
):
    setup = await session.get(FormSetup, setup_id)
    if not setup:
        raise HTTPException(status_code=404, detail="Setup not found")

    if not setup.styling:
        raise HTTPException(status_code=404, detail="Styling not configured")

    return StylingResponse(**setup.styling)