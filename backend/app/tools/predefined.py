import requests
from markdownify import markdownify
import re
from pathlib import Path
import subprocess
from requests.exceptions import RequestException
from smolagents import tool
from bs4 import BeautifulSoup
from io import BytesIO
import pypdf
import os
import time
import random
from typing import Optional, Dict, Any
from urllib.parse import urljoin

# Import googlesearch-python for reliable Google search
try:
    from googlesearch import search
    GOOGLE_SEARCH_AVAILABLE = True
except ImportError:
    GOOGLE_SEARCH_AVAILABLE = False
    print("⚠️ googlesearch-python not available. Install with: pip install googlesearch-python")

# === Reliable Search Tools for LABOS ===
# Simplified and optimized for maximum reliability

@tool
def enhanced_google_search(query: str, num_results: int = 5, include_snippets: bool = True) -> str:
    """Enhanced Google search with rate limiting and retry logic.

    IMPORTANT: This tool may be rate-limited by Google. If you get a 429 error:
    1. Wait a few seconds between searches
    2. Reduce num_results to 3 or fewer
    3. Use alternative search methods (WebSearch, PubMed, etc.)

    Args:
        query: Search query
        num_results: Number of results to return (default: 5, max recommended: 3)
        include_snippets: Whether to include result snippets (default: True)

    Returns:
        Well-formatted search results with titles, URLs, and descriptions
    """
    try:
        if GOOGLE_SEARCH_AVAILABLE:
            # Add random delay to avoid rate limiting (1-3 seconds)
            time.sleep(random.uniform(1.0, 3.0))

            # Retry logic with exponential backoff
            max_retries = 2
            for attempt in range(max_retries):
                try:
                    results = []
                    # Limit to 3 results max to reduce rate limiting risk
                    safe_num_results = min(num_results, 3)
                    search_results = list(search(query, num_results=safe_num_results, advanced=True, pause=2.0))

                    for i, result in enumerate(search_results, 1):
                        if i > safe_num_results:
                            break

                        title = getattr(result, 'title', f'Search Result {i}')
                        url = getattr(result, 'url', 'No URL')
                        description = getattr(result, 'description', 'No description available')

                        if include_snippets:
                            results.append(f"**{i}. {title}**\n🔗 {url}\n📄 {description}\n")
                        else:
                            results.append(f"**{i}. {title}**\n🔗 {url}\n")

                    if results:
                        formatted_results = "\n".join(results)
                        note = f"\n\n💡 Note: Limited to {safe_num_results} results to avoid rate limiting." if num_results > 3 else ""
                        return f"🔍 Enhanced Google Search Results for '{query}':\n\n{formatted_results}{note}"
                    else:
                        return f"No search results found for query: '{query}'"

                except Exception as e:
                    error_str = str(e)
                    if '429' in error_str or 'Too Many Requests' in error_str:
                        if attempt < max_retries - 1:
                            # Exponential backoff: wait 5, 10 seconds
                            wait_time = 5 * (2 ** attempt)
                            print(f"⚠️ Rate limited, waiting {wait_time}s before retry {attempt + 1}/{max_retries}")
                            time.sleep(wait_time)
                            continue
                        else:
                            return f"❌ Google rate limit exceeded. Please:\n1. Wait a few minutes before searching again\n2. Use alternative tools: WebSearch (Brave API), PubMed search, or visit_webpage\n3. Reduce the number of parallel searches\n\nOriginal error: {error_str}"
                    else:
                        raise

        else:
            # Fallback to basic search implementation
            return search_google_basic(query, num_results)

    except Exception as e:
        error_msg = str(e)
        if '429' in error_msg or 'Too Many Requests' in error_msg:
            return f"❌ Google detected unusual traffic (rate limiting).\n\n**Recommended alternatives:**\n1. Use WebSearch tool (Brave API - no rate limits)\n2. Use PubMed search for scientific queries\n3. Wait 2-3 minutes before trying Google search again\n4. Reduce parallel searches\n\nTechnical details: {error_msg}"
        return f"❌ Enhanced Google search failed: {error_msg}"


@tool
def search_google_basic(query: str, num_results: int = 3) -> str:
    """Basic Google search fallback implementation.
    
    Args:
        query: Search query
        num_results: Number of results to return
        
    Returns:
        Basic search results
    """
    try:
        if GOOGLE_SEARCH_AVAILABLE:
            results_string = ""
            search_results = list(search(query, num_results=num_results))
            
            for i, url in enumerate(search_results, 1):
                results_string += f"{i}. {url}\n"
                
            return f"Google Search Results for '{query}':\n\n{results_string}" if results_string else f"No results found for: {query}"
        else:
            return "❌ Google search not available. Please install googlesearch-python: pip install googlesearch-python"
                
    except Exception as e:
        return f"❌ Google search failed: {str(e)}"


@tool
def multi_source_search(query: str, sources: str = "google,serpapi") -> str:
    """Unified search tool with flexible source combinations for different needs.
    
    Args:
        query: Search query
        sources: Comma-separated sources. Options:
        
    • "google" - Basic Google search (~0.3s)
    • "google,serpapi" - Enhanced Google search (~1-2s, DEFAULT)
    • "google,knowledge" - Google + AI knowledge base (~30s)  
    • "google,knowledge,serpapi" - All sources (~45s, most comprehensive)
    
    Quick Guide:
    • Simple queries → "google" 
    • Most queries → "google,serpapi" (DEFAULT - enhanced results, fast)
    • Deep research → "google,knowledge"
    • Comprehensive research → "google,knowledge,serpapi"
        
    Returns:
        Consolidated search results with clear source attribution
    """
    # Check if workflow was cancelled
    try:
        from app.services.workflows import check_cancellation
        check_cancellation()
    except Exception as e:
        if "cancelled" in str(e).lower():
            return f"🛑 Search cancelled: {str(e)}"
    
    source_list = [s.strip().lower() for s in sources.split(",")]
    results = []
    
    # Enhanced Google search (most reliable)
    if "google" in source_list:
        google_result = enhanced_google_search(query, num_results=3)
        if google_result and not google_result.startswith("❌"):
            results.append(f"## 🌐 Enhanced Google Search\n{google_result}")
    
    # SerpAPI search (if API key available and requested)
    if "serpapi" in source_list:
        serpapi_result = search_with_serpapi(query)
        if serpapi_result and not serpapi_result.startswith("⚠️") and not serpapi_result.startswith("❌"):
            results.append(f"## {serpapi_result}")
    
    # Knowledge search (using OpenRouter)
    if "knowledge" in source_list:
        knowledge_result = enhanced_knowledge_search(query)
        if knowledge_result and not knowledge_result.startswith("⚠️") and not knowledge_result.startswith("❌"):
            results.append(f"## {knowledge_result}")
    
    if not results:
        return f"❌ No successful searches completed for query: '{query}'"
    
    consolidated = f"# 🔍 Multi-Source Search Results for: '{query}'\n\n" + "\n\n---\n\n".join(results)
    return consolidated


@tool
def smart_search_router(query: str, domain: str = "auto") -> str:
    """Intelligently route search queries to the most appropriate reliable method.
    
    Args:
        query: Search query
        domain: Domain hint (auto, scientific, general, technical, research)
        
    Returns:
        Results from the most appropriate search method
    """
    query_lower = query.lower()
    
    # Auto-detect domain if not specified
    if domain == "auto":
        scientific_keywords = ["research", "study", "paper", "journal", "publication", "experiment", 
                             "clinical", "trial", "hypothesis", "methodology", "analysis"]
        technical_keywords = ["algorithm", "code", "programming", "software", "framework", 
                             "implementation", "technical", "engineering", "tutorial", "install"]
        
        if any(keyword in query_lower for keyword in scientific_keywords):
            domain = "scientific"
        elif any(keyword in query_lower for keyword in technical_keywords):
            domain = "technical"
        else:
            domain = "general"
    
    # Route to appropriate reliable search method
    if domain == "scientific" or domain == "research":
        # For scientific queries, try enhanced knowledge search first
        knowledge_result = enhanced_knowledge_search(query)
        if knowledge_result and not knowledge_result.startswith("⚠️") and not knowledge_result.startswith("❌"):
            return knowledge_result
        else:
            # Fallback to enhanced Google search
            return enhanced_google_search(query, num_results=5)
    
    elif domain == "technical":
        # Use multi-source for technical queries
        return multi_source_search(query, "google,knowledge")
    
    else:  # general queries
        # Use enhanced Google search for general queries (most reliable)
        return enhanced_google_search(query, num_results=5)


# === Supplementary Search Tools (kept for completeness but not guaranteed reliable) ===

@tool
def search_with_serpapi(query: str, num_results: int = 5) -> str:
    """Advanced Google search using SerpAPI (requires API key).
    
    Args:
        query: Search query
        num_results: Number of results to return (default: 5)
        
    Returns:
        Formatted search results with titles, URLs, and descriptions
    """
    serpapi_key = os.getenv("SERPAPI_API_KEY")
    if not serpapi_key:
        return "⚠️ SerpAPI key not found. Please set SERPAPI_API_KEY in your .env file"
    
    try:
        url = "https://serpapi.com/search"
        params = {
            "engine": "google",
            "q": query,
            "api_key": serpapi_key,
            "num": min(num_results, 10),
            "format": "json"
        }
        
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        
        data = response.json()
        
        if "organic_results" not in data:
            return f"No results found for query: '{query}'"
        
        results = []
        for result in data["organic_results"][:num_results]:
            title = result.get("title", "No title")
            link = result.get("link", "No link")
            snippet = result.get("snippet", "No description")
            
            results.append(f"**{title}**\n{link}\n{snippet}\n")
        
        formatted_results = "\n".join(results)
        return f"🔍 SerpAPI Results for '{query}':\n\n{formatted_results}"
        
    except Exception as e:
        return f"❌ SerpAPI search failed: {str(e)}"


@tool 
def enhanced_knowledge_search(query: str, model_name: str = "gemini-2.5-pro") -> str:
    """Use LLM's internal knowledge to provide detailed information.
    
    Args:
        query: Knowledge query or research question
        model_name: LLM model to use for knowledge expansion
        
    Returns:
        Detailed information based on LLM's training knowledge
    """
    openrouter_key = os.getenv("OPENROUTER_API_KEY")
    if not openrouter_key:
        return "⚠️ OpenRouter API key not found for knowledge search"
    
    try:
        url = "https://openrouter.ai/api/v1/chat/completions"
        
        prompt = f"""You are an assistant to researchers and scientists. Provide detailed, accurate information for this query.

Query: {query}

Please provide:
1. Clear explanation of the topic
2. Key concepts and principles  
3. Current understanding and developments
4. Practical applications
5. Important considerations

Be comprehensive and accurate."""

        payload = {
            "model": f"google/{model_name}",
            "messages": [
                {
                    "role": "system", 
                    "content": "You are a knowledgeable research assistant providing accurate information."
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            "temperature": 0.1,
            "max_tokens": 3000
        }
        
        headers = {
            "Authorization": f"Bearer {openrouter_key}",
            "Content-Type": "application/json"
        }
        
        response = requests.post(url, json=payload, headers=headers, timeout=30)
        response.raise_for_status()
        
        result = response.json()
        
        if "choices" in result and len(result["choices"]) > 0:
            content = result["choices"][0]["message"]["content"]
            return f"🧠 Knowledge Base Response for '{query}':\n\n{content}"
        
        return "Unable to generate knowledge response."
        
    except Exception as e:
        return f"❌ Knowledge search failed: {str(e)}"


# === Legacy Search Function (for compatibility) ===

@tool
def search_google(query: str, num_results: int = 3, language: str = 'en') -> str:
    """
    Legacy Google search function (redirects to reliable implementation).
    
    Args:
        query: The search query
        num_results: Number of results to return (default: 3)
        language: Language code for search results (default: 'en')
    
    Returns:
        Formatted string containing search results
    """
    # Redirect to reliable enhanced Google search
    return enhanced_google_search(query, num_results, include_snippets=True)


# --- Custom Tools ---
@tool
def visit_webpage(url: str) -> str:
    """Visits a webpage at the given URL and returns its content as a markdown string.

    Args:
        url: The URL of the webpage to visit.

    Returns:
        The content of the webpage converted to Markdown, or an error message if the request fails.
    """
    try:
        # Send a GET request to the URL
        response = requests.get(url)
        response.raise_for_status()  # Raise an exception for bad status codes

        # Convert the HTML content to Markdown
        markdown_content = markdownify(response.text).strip()

        # Remove multiple line breaks
        markdown_content = re.sub(r"\n{3,}", "\n\n", markdown_content)

        return markdown_content

    except RequestException as e:
        return f"Error fetching the webpage: {str(e)}"
    except Exception as e:
        return f"An unexpected error occurred: {str(e)}"

@tool
def search_github_repositories(query: str, language: str = "", sort: str = "stars", order: str = "desc", per_page: int = 10) -> str:
    """Search GitHub repositories for packages, models, or projects.
    
    Args:
        query: Search query (e.g., "transformer model", "pytorch CNN", "machine learning")
               TIP: Use simple, focused keywords for better results (restrict to 1-2 keywords). Avoid overly complex compound queries.
               Examples: "ESM protein" vs "ESM-2 ProteinGym DMS prediction embeddings"
        language: Programming language filter (e.g., "Python", "JavaScript")
        sort: Sort results by "stars", "forks", "updated", or "created"
        order: Order results "desc" or "asc"
        per_page: Number of results to return (max 100)
        
    Returns:
        Formatted list of repository information including name, description, stars, and URL
    """
    try:
        # GitHub API endpoint for repository search
        url = "https://api.github.com/search/repositories"
        
        # Build search query
        search_query = query
        if language:
            search_query += f" language:{language}"
            
        params = {
            "q": search_query,
            "sort": sort,
            "order": order,
            "per_page": min(per_page, 100)  # GitHub API limit
        }
        
        # Make request to GitHub API
        response = requests.get(url, params=params)
        response.raise_for_status()
        
        data = response.json()
        repositories = data.get("items", [])
        
        if not repositories:
            return f"No repositories found for query: {query}"
        
        # Format results
        result = f"GitHub搜索结果 (查询: '{query}'):\n\n"
        
        for i, repo in enumerate(repositories, 1):
            name = repo.get("name", "N/A")
            full_name = repo.get("full_name", "N/A")
            description = repo.get("description", "No description available")
            stars = repo.get("stargazers_count", 0)
            forks = repo.get("forks_count", 0)
            language_used = repo.get("language", "N/A")
            html_url = repo.get("html_url", "N/A")
            updated_at = repo.get("updated_at", "N/A")
            
            result += f"{i}. **{name}** ({full_name})\n"
            result += f"   Description: {description}\n"
            result += f"   Language: {language_used} | ⭐ {stars} | 🍴 {forks}\n"
            result += f"   Updated: {updated_at[:10]}\n"
            result += f"   URL: {html_url}\n\n"
        
        result += f"Total found: {data.get('total_count', 0)} repositories"
        return result
        
    except RequestException as e:
        return f"GitHub API request failed: {str(e)}"
    except Exception as e:
        return f"Error searching GitHub repositories: {str(e)}"

@tool
def search_github_code(query: str, language: str = "", filename: str = "", extension: str = "", per_page: int = 10) -> str:
    """Search for code snippets in GitHub repositories.
    
    Args:
        query: Code search query (e.g., "def train_model", "class CNN"), TIP: Use simple, focused keywords for better results (restrict to 1-2 keywords). Avoid overly complex compound queries.
        language: Programming language filter
        filename: Specific filename to search in
        extension: File extension filter (e.g., "py", "js")
        per_page: Number of results to return (max 100)
        
    Returns:
        Code search results with file paths, repository info, and code snippets
    """
    try:
        url = "https://api.github.com/search/code"
        
        # Build search query
        search_query = query
        if language:
            search_query += f" language:{language}"
        if filename:
            search_query += f" filename:{filename}"
        if extension:
            search_query += f" extension:{extension}"
            
        params = {
            "q": search_query,
            "per_page": min(per_page, 100)
        }
        
        response = requests.get(url, params=params)
        response.raise_for_status()
        
        data = response.json()
        code_items = data.get("items", [])
        
        if not code_items:
            return f"未找到相关代码: {query}"
        
        result = f"GitHub代码搜索结果 (查询: '{query}'):\n\n"
        
        for i, item in enumerate(code_items, 1):
            name = item.get("name", "N/A")
            path = item.get("path", "N/A")
            repo_name = item.get("repository", {}).get("full_name", "N/A")
            html_url = item.get("html_url", "N/A")
            
            result += f"{i}. **{name}**\n"
            result += f"   Repository: {repo_name}\n"
            result += f"   Path: {path}\n"
            result += f"   URL: {html_url}\n\n"
        
        result += f"Total found: {data.get('total_count', 0)} code files"
        return result
        
    except RequestException as e:
        return f"GitHub code search failed: {str(e)}"
    except Exception as e:
        return f"Error searching GitHub code: {str(e)}"

@tool
def get_github_repository_info(repo_owner: str, repo_name: str) -> str:
    """Get detailed information about a specific GitHub repository.
    
    Args:
        repo_owner: Repository owner/organization name
        repo_name: Repository name
        
    Returns:
        Detailed repository information including README, releases, and installation instructions
    """
    try:
        # Get repository information
        repo_url = f"https://api.github.com/repos/{repo_owner}/{repo_name}"
        response = requests.get(repo_url)
        response.raise_for_status()
        
        repo_data = response.json()

        # Get README content
        readme_url = f"https://api.github.com/repos/{repo_owner}/{repo_name}/readme"
        try:
            readme_response = requests.get(readme_url)
            readme_response.raise_for_status()
            readme_data = readme_response.json()
            readme_content = requests.get(readme_data["download_url"]).text
        except:
            readme_content = "README not available"
        
        # Get latest release
        releases_url = f"https://api.github.com/repos/{repo_owner}/{repo_name}/releases/latest"
        try:
            release_response = requests.get(releases_url)
            release_response.raise_for_status()
            latest_release = release_response.json()
            release_info = f"最新版本: {latest_release.get('tag_name', 'N/A')} ({latest_release.get('published_at', 'N/A')[:10]})"
        except:
            release_info = "无可用版本信息"
        
        # Format result
        result = f"GitHub仓库详细信息: {repo_owner}/{repo_name}\n\n"
        result += f"描述: {repo_data.get('description', 'N/A')}\n"
        result += f"语言: {repo_data.get('language', 'N/A')}\n"
        result += f"⭐ Stars: {repo_data.get('stargazers_count', 0)}\n"
        result += f"🍴 Forks: {repo_data.get('forks_count', 0)}\n"
        result += f"📁 Size: {repo_data.get('size', 0)} KB\n"
        result += f"📅 创建时间: {repo_data.get('created_at', 'N/A')[:10]}\n"
        result += f"🔄 更新时间: {repo_data.get('updated_at', 'N/A')[:10]}\n"
        result += f"{release_info}\n"
        result += f"🔗 链接: {repo_data.get('html_url', 'N/A')}\n"
        result += f"📄 Clone URL: {repo_data.get('clone_url', 'N/A')}\n\n"
        
        # Add topics/tags if available
        topics = repo_data.get('topics', [])
        if topics:
            result += f"🏷️ Topics: {', '.join(topics)}\n\n"
        
        # Add README content (first 1000 characters)
        if readme_content and readme_content != "README not available":
            result += "📖 README Preview:\n"
            result += "=" * 50 + "\n"
            result += readme_content[:1000]
            if len(readme_content) > 1000:
                result += "\n... (truncated to first 1000 characters)"
            result += "\n" + "=" * 50 + "\n"
        
        return result
        
    except RequestException as e:
        return f"Failed to get GitHub repository info: {str(e)}"
    except Exception as e:
        return f"Error processing GitHub repository info: {str(e)}"

@tool
def run_shell_command(command: str, working_directory: str = ".") -> str:
    """Execute a shell command and return the output.
    
    Args:
        command: The shell command to execute
        working_directory: Optional working directory for the command (default: ".")
        
    Returns:
        Command output or error message
    """
    try:
        result = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            text=True,
            cwd=working_directory,
            timeout=1800  # 30 minute timeout for ML tasks
        )
        
        output = f"Command: {command}\n"
        output += f"Return code: {result.returncode}\n"
        output += f"STDOUT:\n{result.stdout}\n"
        if result.stderr:
            output += f"STDERR:\n{result.stderr}\n"
            
        return output
        
    except subprocess.TimeoutExpired:
        return f"Command timed out after 30 minutes: {command}"
    except Exception as e:
        return f"Error executing command '{command}': {str(e)}"

@tool
def create_conda_environment(env_name: str, python_version: str = "3.9") -> str:
    """Create a new conda environment.
    
    Args:
        env_name: Name of the conda environment
        python_version: Python version for the environment (default: 3.9)
        
    Returns:
        Result of the conda environment creation
    """
    command = f"conda create -n {env_name} python={python_version} -y"
    return run_shell_command(command)

@tool
def install_packages_conda(env_name: str, packages: str) -> str:
    """Install packages in a conda environment.
    
    Args:
        env_name: Name of the conda environment
        packages: Space-separated list of packages to install
        
    Returns:
        Result of the package installation
    """
    command = f"conda activate {env_name} && conda install {packages} -y"
    return run_shell_command(command)

@tool
def install_packages_pip(env_name: str, packages: str) -> str:
    """Install pip packages in a conda environment.
    
    Args:
        env_name: Name of the conda environment
        packages: Space-separated list of pip packages to install
        
    Returns:
        Result of the pip installation
    """
    command = f"conda activate {env_name} && pip install {packages}"
    return run_shell_command(command)

@tool
def check_gpu_status(dummy_param: str = "") -> str:
    """Check GPU status and availability using nvidia-smi.
    
    Args:
        dummy_param: Unused parameter to handle smolagents' automatic parameter passing
    
    Returns:
        GPU status information or error if no GPUs available
    """
    try:
        result = subprocess.run(
            ["nvidia-smi", "--query-gpu=index,name,memory.total,memory.used,memory.free,utilization.gpu", "--format=csv"],
            capture_output=True,
            text=True,
            timeout=30
        )
        
        if result.returncode == 0:
            return f"GPU Status:\n{result.stdout}"
        else:
            return f"Error checking GPU status: {result.stderr}"
            
    except FileNotFoundError:
        return "nvidia-smi not found. No NVIDIA GPUs available or drivers not installed."
    except Exception as e:
        return f"Error checking GPU status: {str(e)}"

@tool
def create_script(script_name: str, script_content: str, directory: str = "/tmp/", script_type: str = "python") -> str:
    """Create a script file.
    
    Args:
        script_name: Name of the script file (should include appropriate extension)
        script_content: Content of the script
        directory: Directory to create the script in (default: /tmp/)
        script_type: Type of script (python, bash, etc.) for informational purposes
        
    Returns:
        Result of script creation
    """
    try:
        script_path = Path(directory) / script_name
        script_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Strip triple quotes if they wrap the entire content
        cleaned_content = script_content.strip()
        if cleaned_content.startswith("'''") and cleaned_content.endswith("'''"):
            cleaned_content = cleaned_content[3:-3].strip()
        elif cleaned_content.startswith('"""') and cleaned_content.endswith('"""'):
            cleaned_content = cleaned_content[3:-3].strip()
        
        with open(script_path, 'w', encoding='utf-8') as f:
            f.write(cleaned_content)
        
        # Make script executable if it's a bash script
        if script_name.endswith('.sh') or script_type.lower() in ['bash', 'shell']:
            import os
            os.chmod(script_path, 0o755)
            
        return f"Successfully created {script_type} script: {script_path}"
        
    except Exception as e:
        return f"Error creating script '{script_name}': {str(e)}"

@tool
def create_and_run_script(script_name: str, script_content: str, directory: str = "/tmp/", env_name: str = None, interpreter: str = "python") -> str:
    """Create and immediately run a script file with validation.
    
    Args:
        script_name: Name of the script file (should include appropriate extension)
        script_content: Content of the script
        directory: Directory to create the script in (default: /tmp/)
        env_name: Name of the conda environment (optional)
        interpreter: Script interpreter (python, bash, etc.) - default: python
        
    Returns:
        Result of script creation and execution
    """
    try:
        # First create the script
        create_result = create_script(script_name, script_content, directory, interpreter)
        if "Error" in create_result:
            return create_result
            
        # Then run it
        script_path = Path(directory) / script_name
        run_result = run_script(str(script_path), env_name, directory, interpreter)
        
        return f"{create_result}\n\nExecution result:\n{run_result}"
        
    except Exception as e:
        return f"Error creating and running script '{script_name}': {str(e)}"

@tool
def run_script(script_path: str, env_name: str = None, working_directory: str = None, interpreter: str = "python") -> str:
    """Run a script with optional conda environment activation.
    
    Args:
        script_path: Path to the script to run
        env_name: Name of the conda environment (optional)
        working_directory: Working directory for the script execution (optional)
        interpreter: Script interpreter (python, bash, etc.) - default: python
        
    Returns:
        Output from the script execution
    """
    # Determine the appropriate command based on file extension and interpreter
    script_name = Path(script_path).name
    
    if script_name.endswith('.sh') or interpreter.lower() in ['bash', 'shell']:
        base_command = f"bash {script_path}"
    elif script_name.endswith('.py') or interpreter.lower() == 'python':
        base_command = f"python {script_path}"
    else:
        # Try to run with specified interpreter
        base_command = f"{interpreter} {script_path}"
    
    # Add conda environment activation if specified
    if env_name:
        command = f"conda activate {env_name} && {base_command}"
    else:
        command = base_command
        
    return run_shell_command(command, working_directory)

@tool
def create_requirements_file(requirements: str, directory: str = ".") -> str:
    """Create a requirements.txt file.
    
    Args:
        requirements: Content of the requirements file (one package per line)
        directory: Directory to create the file in
        
    Returns:
        Result of file creation
    """
    try:
        req_path = Path(directory) / "requirements.txt"
        req_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(req_path, 'w', encoding='utf-8') as f:
            f.write(requirements)
            
        return f"Successfully created requirements.txt: {req_path}"
        
    except Exception as e:
        return f"Error creating requirements.txt: {str(e)}"

@tool
def monitor_training_logs(log_file_path: str, lines: int = 50) -> str:
    """Monitor training logs by reading the last N lines of a log file.
    
    Args:
        log_file_path: Path to the log file
        lines: Number of lines to read from the end (default: 50)
        
    Returns:
        Last N lines of the log file
    """
    try:
        command = f"tail -n {lines} {log_file_path}"
        return run_shell_command(command)
        
    except Exception as e:
        return f"Error reading log file '{log_file_path}': {str(e)}"



@tool
def fetch_supplementary_info_from_doi(doi: str, output_dir: str = "supplementary_info") -> str:
    """
    Fetches supplementary information for a paper given its DOI and returns a research log.

    Args:
        doi: The paper DOI
        output_dir: Directory to save supplementary files (default: "supplementary_info")

    Returns:
        A formatted research log string containing the download process and results
    """
    research_log = []
    research_log.append(f"Starting process for DOI: {doi}")

    # CrossRef API to resolve DOI to a publisher page
    crossref_url = f"https://doi.org/{doi}"
    headers = {"User-Agent": "Mozilla/5.0"}
    response = requests.get(crossref_url, headers=headers)

    if response.status_code != 200:
        log_message = f"Failed to resolve DOI: {doi}. Status Code: {response.status_code}"
        research_log.append(log_message)
        return '\n'.join(research_log)

    publisher_url = response.url
    research_log.append(f"Resolved DOI to publisher page: {publisher_url}")

    # Fetch publisher page
    response = requests.get(publisher_url, headers=headers)
    if response.status_code != 200:
        log_message = f"Failed to access publisher page for DOI {doi}."
        research_log.append(log_message)
        return '\n'.join(research_log)

    # Parse page content
    soup = BeautifulSoup(response.content, "html.parser")
    supplementary_links = []

    # Look for supplementary materials by keywords or links
    for link in soup.find_all("a", href=True):
        href = link.get("href")
        text = link.get_text().lower()
        if "supplementary" in text or "supplemental" in text or "appendix" in text:
            full_url = urljoin(publisher_url, href)
            supplementary_links.append(full_url)
            research_log.append(f"Found supplementary material link: {full_url}")

    if not supplementary_links:
        log_message = f"No supplementary materials found for DOI {doi}."
        research_log.append(log_message)
        return '\n'.join(research_log)

    # Create output directory
    os.makedirs(output_dir, exist_ok=True)
    research_log.append(f"Created output directory: {output_dir}")

    # Download supplementary materials
    downloaded_files = []
    for link in supplementary_links:
        file_name = os.path.join(output_dir, link.split("/")[-1])
        file_response = requests.get(link, headers=headers)
        if file_response.status_code == 200:
            with open(file_name, "wb") as f:
                f.write(file_response.content)
            downloaded_files.append(file_name)
            research_log.append(f"Downloaded file: {file_name}")
        else:
            research_log.append(f"Failed to download file from {link}")

    if downloaded_files:
        research_log.append(f"Successfully downloaded {len(downloaded_files)} file(s).")
    else:
        research_log.append(f"No files could be downloaded for DOI {doi}.")

    return '\n'.join(research_log)

@tool
def query_arxiv(query: str, max_papers: int = 10) -> str:
    """
    Query arXiv for papers based on the provided search query.

    Args:
        query: The search query string
        max_papers: The maximum number of papers to retrieve (default: 10, max: 50)

    Returns:
        The formatted search results or an error message
    """
    import arxiv
    from itertools import islice

    try:
        # Limit max_papers to prevent excessive API calls
        max_papers = min(max_papers, 50)

        # Configure client with page_size equal to max_papers to fetch only ONE page
        # This prevents the library from fetching all 500k+ results
        client = arxiv.Client(
            page_size=max_papers,  # Only fetch what we need
            delay_seconds=3.0,
            num_retries=3
        )

        search = arxiv.Search(
            query=query,
            max_results=max_papers,
            sort_by=arxiv.SortCriterion.Relevance
        )

        # Use islice to absolutely ensure we don't iterate beyond max_papers
        # This is a safety net in case the library still tries to fetch more
        papers = []
        for paper in islice(client.results(search), max_papers):
            papers.append(f"Title: {paper.title}\nSummary: {paper.summary}")

        results = "\n\n".join(papers)
        return results if results else "No papers found on arXiv."
    except Exception as e:
        return f"Error querying arXiv: {e}"


@tool
def query_scholar(query: str, timeout_seconds: int = 30) -> str:
    """
    Query Google Scholar for papers based on the provided search query with timeout handling.

    Args:
        query: The search query string
        timeout_seconds: Maximum seconds to wait before timing out (default: 30)

    Returns:
        A formatted result string, a timeout/rate-limit notice with fallback, or an error message
    """
    try:
        from scholarly import scholarly
    except Exception as e:
        # Library not available; fallback to enhanced Google search
        try:
            return enhanced_google_search(query, num_results=3)
        except Exception:
            return f"Error loading scholarly: {e}"

    # Run the potentially blocking call in a thread to enforce timeout
    import threading

    result_container = {"text": None}

    def worker():
        try:
            search_query = scholarly.search_pubs(query)
            result = next(search_query, None)
            if result:
                title = result.get('bib', {}).get('title', 'N/A')
                year = result.get('bib', {}).get('pub_year', 'N/A')
                venue = result.get('bib', {}).get('venue', 'N/A')
                abstract = result.get('bib', {}).get('abstract', 'N/A')
                result_container["text"] = f"Title: {title}\nYear: {year}\nVenue: {venue}\nAbstract: {abstract}"
            else:
                result_container["text"] = "No results found on Google Scholar."
        except Exception as e:
            msg = str(e)
            # Handle common rate-limit/captcha signals
            if "429" in msg or "captcha" in msg.lower() or "Too Many Requests" in msg:
                result_container["text"] = (
                    "⚠️ Google Scholar rate-limited or CAPTCHA detected. "
                    "Falling back to web search results.\n" + enhanced_google_search(query, num_results=3)
                )
            else:
                result_container["text"] = f"Error querying Google Scholar: {e}"

    thread = threading.Thread(target=worker, daemon=True)
    thread.start()
    thread.join(timeout_seconds)

    if thread.is_alive():
        # Timeout: best-effort fallback
        try:
            fallback = enhanced_google_search(query, num_results=3)
        except Exception:
            fallback = ""
        return (
            f"⚠️ Google Scholar timed out after {timeout_seconds}s. "
            + ("Fallback results:\n" + fallback if fallback else "Please try again later.")
        )

    return result_container["text"] or "No results found."

@tool
def query_pubmed(query: str, max_papers: int = 10, max_retries: int = 3) -> str:
    """
    Query PubMed for papers based on the provided search query.

    Args:
        query: The search query string
        max_papers: The maximum number of papers to retrieve (default: 10)
        max_retries: Maximum number of retry attempts with modified queries (default: 3)

    Returns:
        The formatted search results or an error message
    """
    from pymed import PubMed
    import time

    try:
        pubmed = PubMed(tool="MyTool", email="your-email@example.com")  # Update with a valid email address
        
        # Initial attempt
        papers = list(pubmed.query(query, max_results=max_papers))
        
        # Retry with modified queries if no results
        retries = 0
        while not papers and retries < max_retries:
            retries += 1
            # Simplify query with each retry by removing the last word
            simplified_query = ' '.join(query.split()[:-retries]) if len(query.split()) > retries else query
            time.sleep(1)  # Add delay between requests
            papers = list(pubmed.query(simplified_query, max_results=max_papers))
        
        if papers:
            results = "\n\n".join([f"Title: {paper.title}\nAbstract: {paper.abstract}\nJournal: {paper.journal}" for paper in papers])
            return results
        else:
            return "No papers found on PubMed after multiple query attempts."
    except Exception as e:
        return f"Error querying PubMed: {e}"
    

@tool
def extract_url_content(url: str) -> str:
    """
    Extract the text content of a webpage using requests and BeautifulSoup.
    
    Args:
        url: Webpage URL to extract content from
    
    Returns:
        Text content of the webpage
    """
    try:
        response = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'})
        
        # Check if the response is in text format
        if 'text/plain' in response.headers.get('Content-Type', '') or 'application/json' in response.headers.get('Content-Type', ''):
            return response.text.strip()  # Return plain text or JSON response directly
        
        # If it's HTML, use BeautifulSoup to parse
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Try to find main content first, fallback to body
        content = soup.find('main') or soup.find('article') or soup.body
        
        # Remove unwanted elements
        for element in content(['script', 'style', 'nav', 'header', 'footer', 'aside', 'iframe']):
            element.decompose()
            
        # Extract text with better formatting
        paragraphs = content.find_all(['p', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6'])
        cleaned_text = []
        
        for p in paragraphs:
            text = p.get_text().strip()
            if text:  # Only add non-empty paragraphs
                cleaned_text.append(text)
                
        return '\n\n'.join(cleaned_text)
    except Exception as e:
        return f"Error extracting content from URL: {str(e)}"


@tool
def extract_pdf_content(url: str) -> str:
    """
    Extract the text content of a PDF file given its URL.
    
    Args:
        url: URL of the PDF file to extract text from
        
    Returns:
        The extracted text content from the PDF
    """
    try:
        # Check if the URL ends with .pdf
        if not url.lower().endswith('.pdf'):
            # If not, try to find a PDF link on the page
            response = requests.get(url, timeout=30)
            if response.status_code == 200:
                # Look for PDF links in the HTML content
                pdf_links = re.findall(r'href=[\'"]([^\'"]+\.pdf)[\'"]', response.text)
                if pdf_links:
                    # Use the first PDF link found
                    if not pdf_links[0].startswith('http'):
                        # Handle relative URLs
                        base_url = '/'.join(url.split('/')[:3])
                        url = base_url + pdf_links[0] if pdf_links[0].startswith('/') else base_url + '/' + pdf_links[0]
                    else:
                        url = pdf_links[0]
                else:
                    return f"No PDF file found at {url}. Please provide a direct link to a PDF file."
        
        # Download the PDF
        response = requests.get(url, timeout=30)
        
        # Check if we actually got a PDF file (by checking content type or magic bytes)
        content_type = response.headers.get('Content-Type', '').lower()
        if 'application/pdf' not in content_type and not response.content.startswith(b'%PDF'):
            return f"The URL did not return a valid PDF file. Content type: {content_type}"
        
        pdf_file = BytesIO(response.content)
        
        # Try with pypdf first
        try:
            text = ""
            pdf_reader = pypdf.PdfReader(pdf_file)
            for page_num in range(len(pdf_reader.pages)):
                page = pdf_reader.pages[page_num]
                text += page.extract_text() + "\n\n"
        except Exception as e:
            print(f"Error extracting text from PDF: {str(e)}")
        
        # Clean up the text
        text = re.sub(r'\s+', ' ', text).strip()
        
        if not text:
            return "The PDF file did not contain any extractable text. It may be an image-based PDF requiring OCR."
        
        return text
    
    except requests.exceptions.RequestException as e:
        return f"Error downloading PDF: {str(e)}"
    except Exception as e:
        return f"Error extracting text from PDF: {str(e)}"