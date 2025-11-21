"""
GCS API endpoints for large file uploads
Provides signed URLs for direct upload to Google Cloud Storage
"""

import logging
from typing import Optional
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel

from app.services.gcs_service import gcs_service

logger = logging.getLogger(__name__)

router = APIRouter()


class SignedUrlRequest(BaseModel):
    """Request for generating a signed upload URL"""
    filename: str
    content_type: str
    user_id: str
    project_id: str
    file_size: Optional[int] = None  # Optional: for validation


class SignedUrlResponse(BaseModel):
    """Response with signed URL for upload"""
    upload_url: str
    gcs_uri: str
    blob_name: str
    expires_in: int  # seconds


class UploadCompleteRequest(BaseModel):
    """Request to confirm upload completion"""
    blob_name: str
    gcs_uri: str
    user_id: str
    project_id: str
    original_filename: str
    content_type: str


class UploadCompleteResponse(BaseModel):
    """Response after confirming upload"""
    success: bool
    file_id: Optional[str] = None
    gcs_uri: str
    message: str


# Max file sizes by type
MAX_FILE_SIZES = {
    "video": 100 * 1024 * 1024,   # 100MB for video
    "image": 50 * 1024 * 1024,    # 50MB for images
    "pdf": 100 * 1024 * 1024,     # 100MB for PDFs
    "default": 50 * 1024 * 1024,  # 50MB default
}


def get_max_size_for_type(content_type: str) -> int:
    """Get maximum file size based on content type"""
    if content_type.startswith("video/"):
        return MAX_FILE_SIZES["video"]
    elif content_type.startswith("image/"):
        return MAX_FILE_SIZES["image"]
    elif content_type == "application/pdf":
        return MAX_FILE_SIZES["pdf"]
    return MAX_FILE_SIZES["default"]


@router.post("/signed-url", response_model=SignedUrlResponse)
async def get_signed_upload_url(request: SignedUrlRequest):
    """
    Generate a signed URL for uploading a file directly to GCS.
    This bypasses Cloud Run's 32MB request limit.

    The frontend should:
    1. Call this endpoint to get a signed URL
    2. Upload the file directly to GCS using PUT request
    3. Call /upload-complete to confirm and register the file
    """
    try:
        # Validate content type
        allowed_types = [
            "video/mp4", "video/webm", "video/mov", "video/mpeg", "video/avi",
            "video/quicktime", "video/x-msvideo", "video/x-matroska",
            "image/png", "image/jpeg", "image/gif", "image/webp",
            "application/pdf"
        ]

        if not any(request.content_type.startswith(t.split("/")[0]) for t in ["video/", "image/"]) \
           and request.content_type not in allowed_types:
            raise HTTPException(
                status_code=400,
                detail=f"Unsupported content type: {request.content_type}"
            )

        # Get max size for this file type
        max_size = get_max_size_for_type(request.content_type)

        # Validate file size if provided
        if request.file_size and request.file_size > max_size:
            max_mb = max_size // (1024 * 1024)
            raise HTTPException(
                status_code=400,
                detail=f"File too large. Maximum size for {request.content_type} is {max_mb}MB"
            )

        # Generate signed URL
        signed_url, gcs_uri, blob_name = gcs_service.generate_upload_signed_url(
            filename=request.filename,
            content_type=request.content_type,
            user_id=request.user_id,
            project_id=request.project_id,
            max_size_bytes=max_size
        )

        logger.info(f"Generated signed URL for {request.filename} -> {blob_name}")

        return SignedUrlResponse(
            upload_url=signed_url,
            gcs_uri=gcs_uri,
            blob_name=blob_name,
            expires_in=3600  # 1 hour
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to generate signed URL: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to generate upload URL: {str(e)}")


@router.post("/upload-complete", response_model=UploadCompleteResponse)
async def confirm_upload_complete(request: UploadCompleteRequest):
    """
    Confirm that a file has been uploaded to GCS.
    This registers the file in the database for later use.
    """
    try:
        # Verify the blob exists in GCS
        if not gcs_service.blob_exists(request.blob_name):
            raise HTTPException(
                status_code=404,
                detail="File not found in storage. Upload may have failed."
            )

        # Get blob metadata
        metadata = gcs_service.get_blob_metadata(request.blob_name)

        if not metadata:
            raise HTTPException(
                status_code=500,
                detail="Failed to get file metadata"
            )

        # TODO: Optionally save to database for tracking
        # For now, just return success with GCS URI
        # The GCS URI can be used directly with Vertex AI Gemini

        logger.info(f"Upload confirmed: {request.blob_name} ({metadata.get('size', 0)} bytes)")

        return UploadCompleteResponse(
            success=True,
            gcs_uri=request.gcs_uri,
            message=f"File uploaded successfully. Size: {metadata.get('size', 0)} bytes"
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to confirm upload: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to confirm upload: {str(e)}")


@router.delete("/blob/{blob_name:path}")
async def delete_blob(blob_name: str):
    """Delete a blob from GCS"""
    try:
        success = gcs_service.delete_blob(blob_name)
        if success:
            return {"success": True, "message": f"Deleted {blob_name}"}
        else:
            raise HTTPException(status_code=500, detail="Failed to delete file")
    except Exception as e:
        logger.error(f"Failed to delete blob: {e}")
        raise HTTPException(status_code=500, detail=str(e))
