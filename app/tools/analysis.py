"""
CSV Data Analyzer Tool

This tool provides functionality to read CSV files and perform basic data analysis
including differential expression analysis between tumor and normal samples.
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Union, Any
from scipy import stats
import os
from smolagents import tool


@tool
def csv_data_analyzer(
    file_path: str,
    tumor_columns: Optional[List[str]] = None,
    normal_columns: Optional[List[str]] = None,
    analysis_type: str = "summary",
    alpha: float = 0.05
) -> Dict[str, Any]:
    """
    Reads a CSV file and performs basic data analysis including differential expression.
    
    This tool can perform various types of analysis on CSV data:
    - Summary statistics (mean, std, median, etc.)
    - Differential expression analysis between tumor and normal samples
    - T-tests for statistical significance
    
    Args:
        file_path (str): Path to the CSV file to analyze
        tumor_columns (Optional[List[str]]): List of column names representing tumor samples.
                                           If None, will try to auto-detect columns containing 'tumor'
        normal_columns (Optional[List[str]]): List of column names representing normal samples.
                                            If None, will try to auto-detect columns containing 'normal'
        analysis_type (str): Type of analysis to perform. Options:
                           - "summary": Basic summary statistics
                           - "differential": Differential expression analysis
                           - "both": Both summary and differential analysis
        alpha (float): Significance level for statistical tests (default: 0.05)
    
    Returns:
        Dict[str, Any]: Dictionary containing analysis results with the following structure:
                       - "summary": Summary statistics if requested
                       - "differential": Differential expression results if requested
                       - "metadata": Information about the dataset
    
    Raises:
        FileNotFoundError: If the specified file does not exist
        ValueError: If the file format is invalid or required columns are missing
        Exception: For other data processing errors
    """
    
    try:
        # Validate file existence
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"File not found: {file_path}")
        
        # Read CSV file
        try:
            df = pd.read_csv(file_path, index_col=0)
        except Exception as e:
            raise ValueError(f"Error reading CSV file: {str(e)}")
        
        # Validate that dataframe is not empty
        if df.empty:
            raise ValueError("The CSV file is empty")
        
        # Auto-detect tumor and normal columns if not provided
        if tumor_columns is None:
            tumor_columns = [col for col in df.columns if 'tumor' in col.lower() or 'cancer' in col.lower()]
        
        if normal_columns is None:
            normal_columns = [col for col in df.columns if 'normal' in col.lower() or 'control' in col.lower()]
        
        # Validate column existence
        missing_tumor = [col for col in tumor_columns if col not in df.columns]
        missing_normal = [col for col in normal_columns if col not in df.columns]
        
        if missing_tumor:
            raise ValueError(f"Tumor columns not found in dataset: {missing_tumor}")
        if missing_normal:
            raise ValueError(f"Normal columns not found in dataset: {missing_normal}")
        
        results = {
            "metadata": {
                "file_path": file_path,
                "shape": df.shape,
                "tumor_samples": len(tumor_columns),
                "normal_samples": len(normal_columns),
                "total_features": len(df)
            }
        }
        
        # Perform summary analysis
        if analysis_type in ["summary", "both"]:
            results["summary"] = _perform_summary_analysis(df, tumor_columns, normal_columns)
        
        # Perform differential expression analysis
        if analysis_type in ["differential", "both"]:
            if len(tumor_columns) == 0 or len(normal_columns) == 0:
                raise ValueError("Both tumor and normal columns are required for differential analysis")
            results["differential"] = _perform_differential_analysis(df, tumor_columns, normal_columns, alpha)
        
        return results
        
    except Exception as e:
        return {"error": str(e), "analysis_successful": False}


def _perform_summary_analysis(df: pd.DataFrame, tumor_columns: List[str], normal_columns: List[str]) -> Dict[str, Any]:
    """
    Perform summary statistics analysis on the dataset.
    
    Args:
        df: Input dataframe
        tumor_columns: List of tumor sample columns
        normal_columns: List of normal sample columns
    
    Returns:
        Dictionary containing summary statistics
    """
    summary = {}
    
    # Overall dataset statistics
    summary["overall"] = {
        "mean": df.mean().mean(),
        "std": df.std().mean(),
        "median": df.median().median(),
        "min": df.min().min(),
        "max": df.max().max()
    }
    
    # Tumor samples statistics
    if tumor_columns:
        tumor_data = df[tumor_columns]
        summary["tumor"] = {
            "mean": tumor_data.mean().mean(),
            "std": tumor_data.std().mean(),
            "median": tumor_data.median().median(),
            "sample_count": len(tumor_columns)
        }
    
    # Normal samples statistics
    if normal_columns:
        normal_data = df[normal_columns]
        summary["normal"] = {
            "mean": normal_data.mean().mean(),
            "std": normal_data.std().mean(),
            "median": normal_data.median().median(),
            "sample_count": len(normal_columns)
        }
    
    return summary


def _perform_differential_analysis(df: pd.DataFrame, tumor_columns: List[str], normal_columns: List[str], alpha: float) -> Dict[str, Any]:
    """
    Perform differential expression analysis between tumor and normal samples.
    
    Args:
        df: Input dataframe
        tumor_columns: List of tumor sample columns
        normal_columns: List of normal sample columns
        alpha: Significance level for statistical tests
    
    Returns:
        Dictionary containing differential expression results
    """
    tumor_data = df[tumor_columns]
    normal_data = df[normal_columns]
    
    # Calculate fold changes and statistics for each gene/feature
    results_list = []
    
    for gene in df.index:
        tumor_values = tumor_data.loc[gene].values
        normal_values = normal_data.loc[gene].values
        
        # Remove NaN values
        tumor_values = tumor_values[~np.isnan(tumor_values)]
        normal_values = normal_values[~np.isnan(normal_values)]
        
        if len(tumor_values) == 0 or len(normal_values) == 0:
            continue
        
        # Calculate basic statistics
        tumor_mean = np.mean(tumor_values)
        normal_mean = np.mean(normal_values)
        
        # Calculate fold change (log2)
        if normal_mean != 0:
            fold_change = np.log2(tumor_mean / normal_mean) if tumor_mean > 0 and normal_mean > 0 else 0
        else:
            fold_change = np.inf if tumor_mean > 0 else 0
        
        # Perform t-test
        try:
            t_stat, p_value = stats.ttest_ind(tumor_values, normal_values)
        except:
            t_stat, p_value = np.nan, np.nan
        
        results_list.append({
            "gene": gene,
            "tumor_mean": tumor_mean,
            "normal_mean": normal_mean,
            "fold_change": fold_change,
            "t_statistic": t_stat,
            "p_value": p_value,
            "significant": p_value < alpha if not np.isnan(p_value) else False
        })
    
    # Convert to dataframe for easier manipulation
    results_df = pd.DataFrame(results_list)
    
    # Sort by p-value
    results_df = results_df.sort_values('p_value', na_position='last')
    
    # Calculate summary statistics
    differential_summary = {
        "total_features_tested": len(results_df),
        "significant_features": len(results_df[results_df['significant']]),
        "upregulated": len(results_df[(results_df['significant']) & (results_df['fold_change'] > 0)]),
        "downregulated": len(results_df[(results_df['significant']) & (results_df['fold_change'] < 0)]),
        "alpha_threshold": alpha
    }
    
    # Get top significant results
    top_results = results_df.head(20).to_dict('records')
    
    return {
        "summary": differential_summary,
        "top_results": top_results,
        "all_results": results_df.to_dict('records') if len(results_df) <= 1000 else "Too many results to return all. Use top_results."
    }


# Example usage and testing function
def test_csv_data_analyzer():
    """
    Test function to validate the csv_data_analyzer tool.
    This function creates sample data and tests the tool functionality.
    """
    # Create sample test data
    np.random.seed(42)
    
    # Generate sample gene expression data
    n_genes = 100
    n_tumor_samples = 10
    n_normal_samples = 8
    
    gene_names = [f"Gene_{i:03d}" for i in range(n_genes)]
    tumor_cols = [f"Tumor_Sample_{i+1}" for i in range(n_tumor_samples)]
    normal_cols = [f"Normal_Sample_{i+1}" for i in range(n_normal_samples)]
    
    # Generate realistic expression data
    data = {}
    
    for col in tumor_cols:
        # Tumor samples with some genes upregulated
        data[col] = np.random.lognormal(mean=2, sigma=1, size=n_genes)
        # Make some genes significantly different
        data[col][:20] *= 2  # Upregulated genes
    
    for col in normal_cols:
        # Normal samples
        data[col] = np.random.lognormal(mean=2, sigma=1, size=n_genes)
    
    # Create DataFrame
    test_df = pd.DataFrame(data, index=gene_names)
    
    # Save test data
    test_file = "./new_tools/test_data.csv"
    test_df.to_csv(test_file)
    
    print("Testing csv_data_analyzer tool...")
    
    # Test 1: Summary analysis
    print("\n1. Testing summary analysis...")
    result = csv_data_analyzer(test_file, analysis_type="summary")
    print(f"Summary analysis completed: {'error' not in result}")
    
    # Test 2: Differential analysis
    print("\n2. Testing differential analysis...")
    result = csv_data_analyzer(
        test_file, 
        tumor_columns=tumor_cols, 
        normal_columns=normal_cols,
        analysis_type="differential"
    )
    print(f"Differential analysis completed: {'error' not in result}")
    if 'differential' in result:
        print(f"Found {result['differential']['summary']['significant_features']} significant features")
    
    # Test 3: Both analyses
    print("\n3. Testing combined analysis...")
    result = csv_data_analyzer(
        test_file,
        tumor_columns=tumor_cols,
        normal_columns=normal_cols, 
        analysis_type="both"
    )
    print(f"Combined analysis completed: {'error' not in result}")
    
    # Test 4: Auto-detection
    print("\n4. Testing auto-detection of columns...")
    result = csv_data_analyzer(test_file, analysis_type="both")
    print(f"Auto-detection completed: {'error' not in result}")
    
    # Test 5: Error handling
    print("\n5. Testing error handling...")
    result = csv_data_analyzer("nonexistent_file.csv")
    print(f"Error handling working: {'error' in result}")
    
    print("\nAll tests completed!")
    return True


if __name__ == "__main__":
    test_csv_data_analyzer()