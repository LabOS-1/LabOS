"""
Gemini-Powered Google Search Tool

This tool uses a dedicated Gemini instance with google_search grounding
to perform real-time web searches. This allows agents using function calling
to still access Google Search capabilities.

The key insight: Gemini's google_search grounding is incompatible with
function calling in the SAME request. But we can create a separate Gemini
instance that ONLY uses google_search, and wrap it as a tool for other agents.
"""

import os
import asyncio
from concurrent.futures import TimeoutError as FuturesTimeoutError
from typing import Optional
from smolagents import tool

# Timeout for search operations (seconds)
# Reduced to fail faster when google_search grounding has issues
SEARCH_TIMEOUT = 30

# Lazy import to avoid circular dependencies
_gemini_search_model = None


def _get_gemini_search_model():
    """Get or create a Gemini model dedicated to google_search grounding"""
    global _gemini_search_model

    if _gemini_search_model is None:
        try:
            from langchain_google_genai import ChatGoogleGenerativeAI

            api_key = os.getenv("GOOGLE_API_KEY")
            if not api_key:
                raise ValueError("GOOGLE_API_KEY not found")

            # Create a dedicated Gemini instance for search with timeout
            # IMPORTANT: google_search grounding does NOT support Preview/Experimental models!
            # See: https://ai.google.dev/gemini-api/docs/google-search
            # Supported models: gemini-2.5-pro, gemini-2.5-flash, gemini-2.5-flash-lite, gemini-2.0-flash
            # Use GEMINI_SEARCH_MODEL env var or default to gemini-2.5-flash for grounding support
            search_model = os.getenv("GEMINI_SEARCH_MODEL", "gemini-2.5-flash")
            model = ChatGoogleGenerativeAI(
                model=search_model,
                google_api_key=api_key,
                temperature=0.1,
                max_output_tokens=4096,
                timeout=SEARCH_TIMEOUT,
                max_retries=2,  # Limit retries to fail faster on API issues
            )
            print(f"📡 Using model for Google Search grounding: {search_model}")

            # Bind ONLY google_search (no other tools)
            _gemini_search_model = model.bind_tools([{"google_search": {}}])
            print("✅ Gemini Search model initialized with google_search grounding")

        except Exception as e:
            print(f"❌ Failed to initialize Gemini Search model: {e}")
            raise

    return _gemini_search_model


@tool
def gemini_google_search(query: str) -> str:
    """
    Search the web using Gemini's built-in Google Search grounding.

    This tool leverages Gemini's native integration with Google Search to provide
    real-time, accurate, and grounded search results with source citations.

    Use this for:
    - Latest news and current events
    - Recent research papers and publications
    - Up-to-date information that may not be in training data
    - Fact-checking and verification

    Args:
        query: The search query (be specific for best results)

    Returns:
        Search results with source citations and relevant information

    Example:
        >>> gemini_google_search("latest CRISPR clinical trials 2025")
        >>> gemini_google_search("who won the Nobel Prize in Medicine 2024")
    """
    try:
        model = _get_gemini_search_model()

        # Create a prompt that encourages comprehensive search results
        search_prompt = f"""Search for: {query}

Please provide a comprehensive answer based on the search results. Include:
1. Key findings and facts
2. Source URLs for citations
3. Dates of information when available

Be concise but thorough."""

        # Invoke the model with timeout protection
        try:
            response = model.invoke(search_prompt)
        except Exception as invoke_error:
            if "timeout" in str(invoke_error).lower():
                return f"❌ Gemini Google Search timed out after {SEARCH_TIMEOUT}s. Try a simpler query."
            raise

        # Extract the content
        result = response.content if hasattr(response, 'content') else str(response)

        # Check for grounding metadata (source citations)
        grounding_info = ""
        if hasattr(response, 'response_metadata'):
            metadata = response.response_metadata
            if 'grounding_metadata' in metadata:
                gm = metadata['grounding_metadata']

                # Extract search queries used
                if 'web_search_queries' in gm:
                    queries = gm['web_search_queries']
                    grounding_info += f"\n\n🔍 Search queries: {', '.join(queries)}"

                # Extract source chunks
                if 'grounding_chunks' in gm:
                    chunks = gm['grounding_chunks'][:5]  # Limit to 5 sources
                    if chunks:
                        grounding_info += "\n\n📚 Sources:"
                        for i, chunk in enumerate(chunks, 1):
                            if 'web' in chunk:
                                web = chunk['web']
                                title = web.get('title', 'Source')
                                uri = web.get('uri', '')
                                grounding_info += f"\n  [{i}] {title}: {uri}"

        return f"🌐 **Gemini Google Search Results**\n\n{result}{grounding_info}"

    except Exception as e:
        error_msg = str(e)
        return f"❌ Gemini Google Search failed: {error_msg}\n\nTry using enhanced_google_search or visit_webpage as alternatives."


@tool
def gemini_realtime_search(question: str, context: Optional[str] = None) -> str:
    """
    Get real-time information using Gemini's Google Search grounding.

    This is optimized for question-answering with the latest information.
    Unlike gemini_google_search which returns raw results, this tool
    synthesizes the information into a direct answer.

    Args:
        question: The question to answer with real-time search
        context: Optional context to help focus the search

    Returns:
        A synthesized answer based on real-time search results

    Example:
        >>> gemini_realtime_search("What is the current stock price of NVIDIA?")
        >>> gemini_realtime_search("Who is the current CEO of OpenAI?", context="AI companies")
    """
    try:
        model = _get_gemini_search_model()

        # Build the prompt
        if context:
            prompt = f"""Context: {context}

Question: {question}

Please search for the most current information and provide a direct, accurate answer. Include source citations."""
        else:
            prompt = f"""Question: {question}

Please search for the most current information and provide a direct, accurate answer. Include source citations."""

        try:
            response = model.invoke(prompt)
        except Exception as invoke_error:
            if "timeout" in str(invoke_error).lower():
                return f"❌ Real-time search timed out after {SEARCH_TIMEOUT}s. Try a simpler query."
            raise

        result = response.content if hasattr(response, 'content') else str(response)

        return f"🔍 **Real-time Answer**\n\n{result}"

    except Exception as e:
        return f"❌ Real-time search failed: {str(e)}"
