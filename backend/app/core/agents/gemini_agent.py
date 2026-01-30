"""
Gemini Multimodal Agent - LangChain Implementation
Supports image, video, and PDF analysis using ChatGoogleGenerativeAI
"""

import os
import logging
import base64
from typing import Optional

from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import HumanMessage

logger = logging.getLogger(__name__)

# Maximum file sizes by type (in bytes)
MAX_FILE_SIZES = {
    "image": 20 * 1024 * 1024,      # 20MB for images
    "video": 500 * 1024 * 1024,     # 500MB for videos
    "pdf": 50 * 1024 * 1024,        # 50MB for PDFs
    "default": 20 * 1024 * 1024,    # 20MB default
}

# Retry configuration
MAX_RETRIES = 3


class GeminiMultimodalAgent:
    """
    A specialized agent for handling multimodal content (images, video, PDFs)
    using Google's Gemini models via LangChain.

    Uses ChatGoogleGenerativeAI with base64-encoded file data for analysis.
    """

    def __init__(self):
        """Initialize the Gemini agent with LangChain"""
        self.api_key = os.getenv("GOOGLE_API_KEY")
        self.model_name = os.getenv("GEMINI_MODEL", "gemini-3-pro-preview")
        self.model = None

        if not self.api_key:
            logger.warning("GOOGLE_API_KEY not set. Gemini agent will not function.")
        else:
            try:
                self.model = ChatGoogleGenerativeAI(
                    model=self.model_name,
                    google_api_key=self.api_key,
                    temperature=0.4,
                    max_output_tokens=8192,
                )
                logger.info(f"Gemini Agent initialized with model: {self.model_name} (LangChain)")
            except Exception as e:
                logger.error(f"Failed to initialize ChatGoogleGenerativeAI: {e}")
                self.model = None

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

    def _get_media_type(self, mime_type: str) -> str:
        """Convert MIME type to LangChain media type."""
        if mime_type.startswith("image/"):
            return "image"
        elif mime_type.startswith("video/"):
            return "video"
        elif mime_type == "application/pdf":
            return "file"
        return "file"

    async def analyze_file(self, file_data: bytes, mime_type: str, prompt: str = "Describe this file in detail.") -> str:
        """
        Analyze a file using Gemini via LangChain.

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

        logger.info(f"Sending file ({len(file_data)} bytes, {mime_type}) to Gemini via LangChain...")

        # Use default prompt if generic
        if prompt == "Describe this file in detail.":
            prompt = self._get_default_prompt(mime_type)

        # Encode file data to base64
        base64_data = base64.b64encode(file_data).decode("utf-8")

        # Get media type for LangChain
        media_type = self._get_media_type(mime_type)

        # Create multimodal message using LangChain format
        try:
            message = HumanMessage(
                content=[
                    {"type": "text", "text": prompt},
                    {
                        "type": media_type,
                        "base64": base64_data,
                        "mime_type": mime_type
                    }
                ]
            )

            # Invoke the model
            response = await self.model.ainvoke([message])

            logger.info("Gemini analysis complete (LangChain).")
            return response.content

        except Exception as e:
            error_msg = f"Error analyzing file with Gemini (LangChain): {str(e)}"
            logger.error(error_msg, exc_info=True)
            return error_msg

    async def analyze_gcs_file(self, gcs_uri: str, mime_type: str, prompt: str = "") -> str:
        """
        Analyze a file from GCS using Gemini via LangChain.
        This method supports files up to 2GB.

        Args:
            gcs_uri: GCS URI (e.g., 'gs://bucket-name/path/to/file.mp4')
            mime_type: MIME type of the file
            prompt: Instruction for analysis

        Returns:
            String description/analysis of the file
        """
        if not self.model:
            return "Error: Gemini API key not configured."

        if not gcs_uri.startswith("gs://"):
            return f"Error: Invalid GCS URI format. Expected 'gs://bucket/path', got: {gcs_uri}"

        # Use default prompt if not provided
        if not prompt:
            prompt = self._get_default_prompt(mime_type)

        logger.info(f"Analyzing GCS file via LangChain: {gcs_uri}")

        # Get media type for LangChain
        media_type = self._get_media_type(mime_type)

        try:
            # Create message with GCS URL
            message = HumanMessage(
                content=[
                    {"type": "text", "text": prompt},
                    {
                        "type": media_type,
                        "url": gcs_uri,
                        "mime_type": mime_type
                    }
                ]
            )

            # Invoke the model
            response = await self.model.ainvoke([message])

            logger.info("GCS analysis complete (LangChain).")
            return response.content

        except Exception as e:
            error_msg = f"Error analyzing GCS file with Gemini (LangChain): {str(e)}"
            logger.error(error_msg, exc_info=True)
            return error_msg


# Singleton instance
gemini_agent = GeminiMultimodalAgent()
