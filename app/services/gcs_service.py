"""
Google Cloud Storage Service
Handles file uploads via signed URLs for large file support (bypassing Cloud Run 32MB limit)
"""

import os
import uuid
import logging
from datetime import timedelta
from typing import Optional, Tuple
from google.cloud import storage
from google.cloud.exceptions import GoogleCloudError
from google.auth import compute_engine, default
from google.auth.transport import requests as auth_requests
import google.auth

logger = logging.getLogger(__name__)

# GCS Configuration
GCS_BUCKET_NAME = os.getenv("GCS_BUCKET_NAME", "labos-uploads")
GCS_SIGNED_URL_EXPIRATION = int(os.getenv("GCS_SIGNED_URL_EXPIRATION", "3600"))  # 1 hour default
GCS_PROJECT_ID = os.getenv("GCP_PROJECT_ID", "semiotic-sylph-470501-q5")
ENVIRONMENT = os.getenv("ENVIRONMENT", "development")


class GCSService:
    """Service for Google Cloud Storage operations"""

    def __init__(self):
        self._client: Optional[storage.Client] = None
        self._bucket: Optional[storage.Bucket] = None
        self._signing_credentials = None

    @property
    def client(self) -> storage.Client:
        """Lazy initialization of GCS client"""
        if self._client is None:
            try:
                # In Cloud Run, uses default service account automatically
                self._client = storage.Client(project=GCS_PROJECT_ID)
                logger.info(f"GCS client initialized for project: {GCS_PROJECT_ID}")
            except Exception as e:
                logger.error(f"Failed to initialize GCS client: {e}")
                raise
        return self._client

    @property
    def bucket(self) -> storage.Bucket:
        """Get the configured bucket"""
        if self._bucket is None:
            self._bucket = self.client.bucket(GCS_BUCKET_NAME)
            logger.info(f"Using GCS bucket: {GCS_BUCKET_NAME}")
        return self._bucket

    def _get_signing_credentials(self):
        """
        Get credentials that can sign URLs.
        In Cloud Run, we use IAM signing via compute_engine.IDTokenCredentials.
        Locally, we need a service account key file.
        """
        if self._signing_credentials is not None:
            return self._signing_credentials

        if ENVIRONMENT == "production":
            # In Cloud Run, use the default compute credentials with IAM signing
            try:
                credentials, project = default()
                # For Cloud Run, we need to use the service account email for signing
                auth_request = auth_requests.Request()
                credentials.refresh(auth_request)

                # Get the service account email from metadata server
                import requests
                try:
                    response = requests.get(
                        "http://metadata.google.internal/computeMetadata/v1/instance/service-accounts/default/email",
                        headers={"Metadata-Flavor": "Google"},
                        timeout=2
                    )
                    service_account_email = response.text
                    logger.info(f"Using service account for signing: {service_account_email}")

                    # Create signing credentials using IAM
                    from google.auth import iam
                    from google.auth.transport import requests as google_auth_requests

                    signer = iam.Signer(
                        google_auth_requests.Request(),
                        credentials,
                        service_account_email
                    )

                    from google.oauth2 import service_account
                    self._signing_credentials = service_account.Credentials(
                        signer=signer,
                        service_account_email=service_account_email,
                        token_uri="https://oauth2.googleapis.com/token",
                        project_id=GCS_PROJECT_ID
                    )
                    return self._signing_credentials
                except Exception as e:
                    logger.warning(f"Could not get service account from metadata: {e}")
                    raise
            except Exception as e:
                logger.error(f"Failed to get signing credentials in production: {e}")
                raise
        else:
            # Local development - check for service account key file
            key_file = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
            if key_file and os.path.exists(key_file):
                from google.oauth2 import service_account
                self._signing_credentials = service_account.Credentials.from_service_account_file(key_file)
                logger.info(f"Using service account key file: {key_file}")
                return self._signing_credentials
            else:
                # No key file - cannot sign locally without it
                raise ValueError(
                    "Cannot generate signed URLs in development without a service account key file. "
                    "Set GOOGLE_APPLICATION_CREDENTIALS to a service account key JSON file, "
                    "or test in production environment."
                )

    def generate_upload_signed_url(
        self,
        filename: str,
        content_type: str,
        user_id: str,
        project_id: str,
        max_size_bytes: int = 100 * 1024 * 1024  # 100MB default
    ) -> Tuple[str, str, str]:
        """
        Generate a signed URL for uploading a file directly to GCS.

        Args:
            filename: Original filename
            content_type: MIME type of the file
            user_id: User ID for organizing files
            project_id: Project ID for organizing files
            max_size_bytes: Maximum allowed file size

        Returns:
            Tuple of (signed_url, gcs_uri, blob_name)
        """
        # Generate unique blob name
        file_ext = os.path.splitext(filename)[1] if filename else ""
        unique_id = uuid.uuid4().hex
        blob_name = f"uploads/{user_id}/{project_id}/{unique_id}{file_ext}"

        blob = self.bucket.blob(blob_name)

        # Get signing credentials
        signing_credentials = self._get_signing_credentials()

        # Generate signed URL for upload (PUT request)
        # Note: We don't include x-goog-content-length-range in signed headers
        # because it causes CORS issues. File size validation is done on confirm.
        signed_url = blob.generate_signed_url(
            version="v4",
            expiration=timedelta(seconds=GCS_SIGNED_URL_EXPIRATION),
            method="PUT",
            content_type=content_type,
            credentials=signing_credentials
        )

        gcs_uri = f"gs://{GCS_BUCKET_NAME}/{blob_name}"

        logger.info(f"Generated signed URL for upload: {blob_name}")

        return signed_url, gcs_uri, blob_name

    def generate_download_signed_url(self, blob_name: str) -> str:
        """
        Generate a signed URL for downloading a file from GCS.

        Args:
            blob_name: The blob name in GCS

        Returns:
            Signed URL for download
        """
        blob = self.bucket.blob(blob_name)

        signed_url = blob.generate_signed_url(
            version="v4",
            expiration=timedelta(seconds=GCS_SIGNED_URL_EXPIRATION),
            method="GET"
        )

        return signed_url

    def delete_blob(self, blob_name: str) -> bool:
        """
        Delete a blob from GCS.

        Args:
            blob_name: The blob name to delete

        Returns:
            True if deleted successfully
        """
        try:
            blob = self.bucket.blob(blob_name)
            blob.delete()
            logger.info(f"Deleted blob: {blob_name}")
            return True
        except GoogleCloudError as e:
            logger.error(f"Failed to delete blob {blob_name}: {e}")
            return False

    def blob_exists(self, blob_name: str) -> bool:
        """Check if a blob exists in GCS"""
        blob = self.bucket.blob(blob_name)
        return blob.exists()

    def get_blob_metadata(self, blob_name: str) -> Optional[dict]:
        """Get metadata for a blob"""
        try:
            blob = self.bucket.blob(blob_name)
            blob.reload()
            return {
                "name": blob.name,
                "size": blob.size,
                "content_type": blob.content_type,
                "created": blob.time_created.isoformat() if blob.time_created else None,
                "updated": blob.updated.isoformat() if blob.updated else None,
                "gcs_uri": f"gs://{GCS_BUCKET_NAME}/{blob_name}"
            }
        except GoogleCloudError as e:
            logger.error(f"Failed to get blob metadata {blob_name}: {e}")
            return None


# Singleton instance
gcs_service = GCSService()
