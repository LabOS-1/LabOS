"""
Gemini Multimodal Agent
Supports both direct file upload (small files) and GCS URI (large files via Vertex AI)
"""

import os
import logging
import asyncio
from functools import partial
from typing import Optional

import google.generativeai as genai
from google.generativeai.types import GenerationConfig

from app.config import AI_MODELS

logger = logging.getLogger(__name__)

# Maximum file sizes by type (in bytes)
MAX_FILE_SIZES = {
    "image": 20 * 1024 * 1024,      # 20MB for images
    "video": 500 * 1024 * 1024,     # 500MB for videos (via GCS)
    "pdf": 50 * 1024 * 1024,        # 50MB for PDFs
    "default": 20 * 1024 * 1024,    # 20MB default
}

# Retry configuration
MAX_RETRIES = 3
RETRY_DELAY_BASE = 1.0  # seconds, will be multiplied by attempt number

# GCS configuration
GCS_PROJECT_ID = os.getenv("GCP_PROJECT_ID", "semiotic-sylph-470501-q5")


class GeminiMultimodalAgent:
    """
    A specialized agent for handling multimodal content (images, video, large text)
    using Google's Gemini models.

    Supports two modes:
    1. Direct upload (small files < 32MB) - uses google-generativeai SDK
    2. GCS URI (large files) - uses vertexai SDK with Vertex AI
    """

    def __init__(self):
        self.api_key = AI_MODELS.get("gemini", {}).get("api_key")
        self.model = None
        self.vertex_client = None

        if not self.api_key:
            logger.warning("GOOGLE_API_KEY not set. Gemini agent will not function.")
        else:
            # Initialize standard Gemini API for small files
            genai.configure(api_key=self.api_key)
            self.model_name = AI_MODELS.get("gemini", {}).get("model", "gemini-2.5-flash-preview-05-20")

            self.generation_config = GenerationConfig(
                temperature=0.4,
                max_output_tokens=8192,
            )

            self.model = genai.GenerativeModel(
                self.model_name,
                generation_config=self.generation_config
            )
            logger.info(f"Gemini Agent initialized with model: {self.model_name}")

            # Try to initialize Vertex AI client for GCS support
            self._init_vertex_client()

    def _init_vertex_client(self):
        """Initialize Vertex AI client for GCS URI support"""
        try:
            import vertexai
            from vertexai.generative_models import GenerativeModel

            # Initialize Vertex AI with project and location
            vertexai.init(project=GCS_PROJECT_ID, location="us-central1")

            # Store the model class for later use
            self.vertex_model = GenerativeModel("gemini-2.0-flash-001")
            self.vertex_client = True  # Flag to indicate Vertex AI is available
            logger.info(f"Vertex AI client initialized for GCS support (project: {GCS_PROJECT_ID})")
        except ImportError as e:
            logger.warning(f"vertexai not installed. GCS URI support disabled. Error: {e}")
            self.vertex_client = None
            self.vertex_model = None
        except Exception as e:
            logger.warning(f"Failed to initialize Vertex AI client: {e}")
            self.vertex_client = None
            self.vertex_model = None

    def _get_max_file_size(self, mime_type: str) -> int:
        """Get the maximum allowed file size based on mime type."""
        if mime_type.startswith("image/"):
            return MAX_FILE_SIZES["image"]
        elif mime_type.startswith("video/"):
            return MAX_FILE_SIZES["video"]
        elif mime_type == "application/pdf":
            return MAX_FILE_SIZES["pdf"]
        return MAX_FILE_SIZES["default"]

    def _get_default_prompt(self, mime_type: str) -> str:
        """Get the default prompt based on mime type."""
        if mime_type.startswith("image/"):
            return "Describe this image in detail. Include visual features, text, and context."
        elif mime_type.startswith("video/"):
            return "Watch this video and provide a detailed summary of events, visual content, and any spoken audio."
        elif mime_type == "application/pdf":
            return "Analyze this PDF document. Summarize the key points, extract important data, and describe its structure."
        return "Describe this file in detail."

    def _generate_content_sync(self, prompt: str, file_part: dict) -> str:
        """Synchronous wrapper for generate_content (to be run in executor)."""
        response = self.model.generate_content([prompt, file_part])
        return response.text

    def _generate_content_from_gcs_sync(self, prompt: str, gcs_uri: str, mime_type: str) -> str:
        """Synchronous wrapper for Vertex AI with GCS URI."""
        from vertexai.generative_models import Part

        # Create a Part from GCS URI
        file_part = Part.from_uri(uri=gcs_uri, mime_type=mime_type)

        # Generate content using Vertex AI model
        response = self.vertex_model.generate_content([prompt, file_part])
        return response.text

    async def analyze_file(self, file_data: bytes, mime_type: str, prompt: str = "Describe this file in detail.") -> str:
        """
        Analyze a file using Gemini (direct upload for small files).

        Args:
            file_data: Raw bytes of the file
            mime_type: MIME type (e.g., 'image/jpeg', 'video/mp4', 'application/pdf')
            prompt: Instruction for analysis

        Returns:
            String description/analysis of the file
        """
        if not self.model:
            return "Error: Gemini API key not configured."

        # Validate file size
        max_size = self._get_max_file_size(mime_type)
        if len(file_data) > max_size:
            error_msg = f"File size ({len(file_data)} bytes) exceeds maximum allowed size ({max_size} bytes) for {mime_type}"
            logger.error(error_msg)
            return f"Error: {error_msg}"

        logger.info(f"Sending file ({len(file_data)} bytes, {mime_type}) to Gemini for analysis...")

        # Prepare the content parts
        file_part = {
            "mime_type": mime_type,
            "data": file_data
        }

        # Use default prompt if generic
        if prompt == "Describe this file in detail.":
            prompt = self._get_default_prompt(mime_type)

        # Retry loop with exponential backoff
        last_error = None
        for attempt in range(1, MAX_RETRIES + 1):
            try:
                loop = asyncio.get_event_loop()
                result_text = await loop.run_in_executor(
                    None,
                    partial(self._generate_content_sync, prompt, file_part)
                )

                logger.info("Gemini analysis complete.")
                return result_text

            except Exception as e:
                last_error = e
                logger.warning(f"Gemini analysis attempt {attempt}/{MAX_RETRIES} failed: {e}")

                if attempt < MAX_RETRIES:
                    delay = RETRY_DELAY_BASE * attempt
                    logger.info(f"Retrying in {delay} seconds...")
                    await asyncio.sleep(delay)

        logger.error(f"All {MAX_RETRIES} attempts failed for Gemini analysis: {last_error}", exc_info=True)
        return f"Error analyzing file with Gemini after {MAX_RETRIES} attempts: {str(last_error)}"

    async def analyze_gcs_file(self, gcs_uri: str, mime_type: str, prompt: str = "") -> str:
        """
        Analyze a file from GCS using Vertex AI Gemini.
        This method supports files up to 2GB.

        Args:
            gcs_uri: GCS URI (e.g., 'gs://bucket-name/path/to/file.mp4')
            mime_type: MIME type of the file
            prompt: Instruction for analysis

        Returns:
            String description/analysis of the file
        """
        if not self.vertex_client:
            return "Error: Vertex AI client not initialized. GCS file analysis unavailable."

        if not gcs_uri.startswith("gs://"):
            return f"Error: Invalid GCS URI format. Expected 'gs://bucket/path', got: {gcs_uri}"

        # Use default prompt if not provided
        if not prompt:
            prompt = self._get_default_prompt(mime_type)

        logger.info(f"Analyzing GCS file via Vertex AI: {gcs_uri}")

        # Retry loop
        last_error = None
        for attempt in range(1, MAX_RETRIES + 1):
            try:
                loop = asyncio.get_event_loop()
                result_text = await loop.run_in_executor(
                    None,
                    partial(self._generate_content_from_gcs_sync, prompt, gcs_uri, mime_type)
                )

                logger.info("Vertex AI GCS analysis complete.")
                return result_text

            except Exception as e:
                last_error = e
                logger.warning(f"Vertex AI analysis attempt {attempt}/{MAX_RETRIES} failed: {e}")

                if attempt < MAX_RETRIES:
                    delay = RETRY_DELAY_BASE * attempt
                    logger.info(f"Retrying in {delay} seconds...")
                    await asyncio.sleep(delay)

        logger.error(f"All {MAX_RETRIES} attempts failed for Vertex AI analysis: {last_error}", exc_info=True)
        return f"Error analyzing GCS file with Vertex AI after {MAX_RETRIES} attempts: {str(last_error)}"


# Singleton instance
gemini_agent = GeminiMultimodalAgent()
