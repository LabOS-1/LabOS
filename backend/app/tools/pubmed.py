"""PubMed Search Tool for Scientific Literature

This module provides a tool for searching PubMed using the NCBI E-utilities API
to find scientific literature and extract relevant paper details.
"""

import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from typing import List, Dict, Any, Optional
import json
import time
import logging
from smolagents import tool

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class PubMedAPIError(Exception):
    """Custom exception for PubMed API errors"""
    pass

class RateLimitError(Exception):
    """Custom exception for rate limit errors"""
    pass

@tool
def pubmed_search(
    query: str,
    max_results: int = 10,
    sort: str = "relevance",
    email: Optional[str] = None
) -> str:
    """
    Search PubMed for scientific literature using NCBI E-utilities API.
    
    This tool searches PubMed database and returns paper details including titles,
    authors, publication dates, and PubMed IDs/URLs.
    
    Args:
        query (str): Search query string (e.g., "machine learning healthcare")
        max_results (int, optional): Maximum number of results to return (default: 10, max: 100)
        sort (str, optional): Sort order - "relevance", "pub_date", "author" (default: "relevance")
        email (str, optional): Email address for API requests (recommended but not required)
    
    Returns:
        str: JSON formatted string containing search results with paper details
        
    Examples:
        >>> results = pubmed_search("COVID-19 vaccines", max_results=5)
        >>> results = pubmed_search("machine learning", max_results=20, sort="pub_date")
    """
    try:
        # Input validation
        if not query or not query.strip():
            raise ValueError("Query cannot be empty")
        
        query = query.strip()
        max_results = max(1, min(max_results, 100))  # Clamp between 1 and 100
        
        if sort not in ["relevance", "pub_date", "author"]:
            sort = "relevance"
        
        logger.info(f"Searching PubMed for: '{query}' (max_results: {max_results}, sort: {sort})")
        
        # Step 1: Search PubMed to get PMIDs
        pmids = _search_pubmed(query, max_results, sort, email)
        
        if not pmids:
            return json.dumps({
                "query": query,
                "total_results": 0,
                "papers": [],
                "message": "No results found for the given query"
            })
        
        # Step 2: Fetch detailed information for the PMIDs
        papers = _fetch_paper_details(pmids, email)
        
        result = {
            "query": query,
            "total_results": len(papers),
            "papers": papers
        }
        
        return json.dumps(result, indent=2)
        
    except ValueError as e:
        logger.error(f"Input validation error: {e}")
        return json.dumps({"error": f"Input validation error: {str(e)}"})
    except RateLimitError as e:
        logger.error(f"Rate limit error: {e}")
        return json.dumps({"error": f"Rate limit exceeded: {str(e)}"})
    except PubMedAPIError as e:
        logger.error(f"PubMed API error: {e}")
        return json.dumps({"error": f"PubMed API error: {str(e)}"})
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        return json.dumps({"error": f"Unexpected error: {str(e)}"})

def _search_pubmed(query: str, max_results: int, sort: str, email: Optional[str]) -> List[str]:
    """
    Search PubMed and return list of PMIDs
    
    Args:
        query: Search query
        max_results: Maximum number of results
        sort: Sort order
        email: Email for API requests
    
    Returns:
        List of PubMed IDs (PMIDs)
    """
    base_url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi"
    
    # Map sort options to PubMed sort parameters
    sort_map = {
        "relevance": "relevance",
        "pub_date": "pub+date",
        "author": "author"
    }
    
    params = {
        "db": "pubmed",
        "term": query,
        "retmax": str(max_results),
        "retmode": "xml",
        "sort": sort_map.get(sort, "relevance"),
        "tool": "pubmed_search_tool",
        "version": "1.0"
    }
    
    if email:
        params["email"] = email
    
    # Build URL
    url = f"{base_url}?{urllib.parse.urlencode(params)}"
    
    try:
        # Add delay to respect rate limits
        time.sleep(0.1)
        
        with urllib.request.urlopen(url, timeout=30) as response:
            if response.status != 200:
                raise PubMedAPIError(f"HTTP {response.status}: {response.reason}")
            
            xml_data = response.read()
            
        # Parse XML response
        root = ET.fromstring(xml_data)
        
        # Check for errors
        error_list = root.find("ErrorList")
        if error_list is not None:
            errors = [err.text for err in error_list.findall("PhraseNotFound")]
            if errors:
                logger.warning(f"PubMed search warnings: {errors}")
        
        # Extract PMIDs
        id_list = root.find("IdList")
        if id_list is None:
            return []
        
        pmids = [id_elem.text for id_elem in id_list.findall("Id")]
        
        logger.info(f"Found {len(pmids)} PMIDs")
        return pmids
        
    except urllib.error.HTTPError as e:
        if e.code == 429:
            raise RateLimitError("Too many requests. Please wait and try again.")
        else:
            raise PubMedAPIError(f"HTTP error {e.code}: {e.reason}")
    except urllib.error.URLError as e:
        raise PubMedAPIError(f"URL error: {e.reason}")
    except ET.ParseError as e:
        raise PubMedAPIError(f"XML parsing error: {e}")

def _fetch_paper_details(pmids: List[str], email: Optional[str]) -> List[Dict[str, Any]]:
    """
    Fetch detailed information for a list of PMIDs
    
    Args:
        pmids: List of PubMed IDs
        email: Email for API requests
    
    Returns:
        List of paper details dictionaries
    """
    if not pmids:
        return []
    
    base_url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi"
    
    params = {
        "db": "pubmed",
        "id": ",".join(pmids),
        "retmode": "xml",
        "tool": "pubmed_search_tool",
        "version": "1.0"
    }
    
    if email:
        params["email"] = email
    
    url = f"{base_url}?{urllib.parse.urlencode(params)}"
    
    try:
        # Add delay to respect rate limits
        time.sleep(0.1)
        
        with urllib.request.urlopen(url, timeout=30) as response:
            if response.status != 200:
                raise PubMedAPIError(f"HTTP {response.status}: {response.reason}")
            
            xml_data = response.read()
        
        # Parse XML response
        root = ET.fromstring(xml_data)
        
        papers = []
        
        for article in root.findall(".//PubmedArticle"):
            paper = _extract_paper_info(article)
            if paper:
                papers.append(paper)
        
        logger.info(f"Extracted details for {len(papers)} papers")
        return papers
        
    except urllib.error.HTTPError as e:
        if e.code == 429:
            raise RateLimitError("Too many requests. Please wait and try again.")
        else:
            raise PubMedAPIError(f"HTTP error {e.code}: {e.reason}")
    except urllib.error.URLError as e:
        raise PubMedAPIError(f"URL error: {e.reason}")
    except ET.ParseError as e:
        raise PubMedAPIError(f"XML parsing error: {e}")

def _extract_paper_info(article_elem: ET.Element) -> Optional[Dict[str, Any]]:
    """
    Extract paper information from a PubmedArticle XML element
    
    Args:
        article_elem: XML element containing article data
    
    Returns:
        Dictionary containing paper information or None if extraction fails
    """
    try:
        paper = {}
        
        # Extract PMID
        pmid_elem = article_elem.find(".//PMID")
        paper["pmid"] = pmid_elem.text if pmid_elem is not None else "Unknown"
        
        # Create PubMed URL
        if paper["pmid"] != "Unknown":
            paper["pubmed_url"] = f"https://pubmed.ncbi.nlm.nih.gov/{paper['pmid']}"
        else:
            paper["pubmed_url"] = None
        
        # Extract title
        title_elem = article_elem.find(".//ArticleTitle")
        paper["title"] = title_elem.text if title_elem is not None else "Title not available"
        
        # Extract authors
        authors = []
        author_list = article_elem.find(".//AuthorList")
        if author_list is not None:
            for author in author_list.findall("Author"):
                last_name = author.find("LastName")
                first_name = author.find("ForeName")
                initials = author.find("Initials")
                
                if last_name is not None:
                    name_parts = [last_name.text]
                    if first_name is not None:
                        name_parts.append(first_name.text)
                    elif initials is not None:
                        name_parts.append(initials.text)
                    
                    authors.append(" ".join(name_parts))
        
        paper["authors"] = authors
        
        # Extract journal information
        journal_elem = article_elem.find(".//Journal/Title")
        if journal_elem is None:
            journal_elem = article_elem.find(".//Journal/ISOAbbreviation")
        paper["journal"] = journal_elem.text if journal_elem is not None else "Journal not available"
        
        # Extract publication date
        pub_date = _extract_publication_date(article_elem)
        paper["publication_date"] = pub_date
        
        # Extract abstract
        abstract_elem = article_elem.find(".//Abstract/AbstractText")
        if abstract_elem is not None:
            paper["abstract"] = abstract_elem.text
        else:
            paper["abstract"] = "Abstract not available"
        
        # Extract DOI if available
        doi_elem = article_elem.find(".//ArticleId[@IdType='doi']")
        paper["doi"] = doi_elem.text if doi_elem is not None else None
        
        return paper
        
    except Exception as e:
        logger.error(f"Error extracting paper info: {e}")
        return None

def _extract_publication_date(article_elem: ET.Element) -> str:
    """
    Extract publication date from article XML
    
    Args:
        article_elem: XML element containing article data
    
    Returns:
        Publication date string
    """
    # Try to get publication date from different possible locations
    pub_date_elem = article_elem.find(".//PubDate")
    
    if pub_date_elem is not None:
        year_elem = pub_date_elem.find("Year")
        month_elem = pub_date_elem.find("Month")
        day_elem = pub_date_elem.find("Day")
        
        date_parts = []
        if year_elem is not None:
            date_parts.append(year_elem.text)
        if month_elem is not None:
            date_parts.append(month_elem.text)
        if day_elem is not None:
            date_parts.append(day_elem.text)
        
        if date_parts:
            return "-".join(date_parts)
    
    # Try alternative date format
    medline_date = pub_date_elem.find("MedlineDate") if pub_date_elem is not None else None
    if medline_date is not None:
        return medline_date.text
    
    return "Date not available"

if __name__ == "__main__":
    # Test the tool
    print("Testing PubMed Search Tool...")
    
    # Test with a simple query
    result = pubmed_search("COVID-19 vaccines", max_results=3)
    print(result)