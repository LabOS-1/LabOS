"""
Plotting tools for data visualization
All visualization tools return base64 encoded images with metadata
"""

import matplotlib
matplotlib.use('Agg')  # Non-interactive backend for server use
import matplotlib.pyplot as plt
import seaborn as sns
import pandas as pd
import numpy as np
import base64
import json
from io import BytesIO
from pathlib import Path
from smolagents import tool

# Set seaborn style for better looking plots
sns.set_style("whitegrid")
plt.rcParams['figure.dpi'] = 150
plt.rcParams['savefig.dpi'] = 150

def _encode_image_to_base64(file_path: str) -> str:
    """Convert image file to base64 string"""
    with open(file_path, 'rb') as f:
        image_data = f.read()
        base64_image = base64.b64encode(image_data).decode('utf-8')
    return f"data:image/png;base64,{base64_image}"

def _save_and_register_plot(
    file_path: str, 
    chart_type: str, 
    title: str,
    description: str = ""
) -> dict:
    """
    Save plot file and register in database.
    Returns metadata including base64 for workflow display.
    """
    try:
        # Convert to base64
        base64_image = _encode_image_to_base64(file_path)
        
        # Register file in database
        from app.tools.core.files import save_agent_file
        file_result = save_agent_file(
            file_path=file_path,
            category="visualization",
            description=description or f"{chart_type}: {title}"
        )
        
        # Parse file_id from result
        # Format: "✅ File 'filename' saved successfully (ID: uuid)"
        import re
        file_id_match = re.search(r'\(ID:\s*([a-f0-9-]+)\)', file_result)
        file_id = file_id_match.group(1) if file_id_match else None

        # Optimization: Only include base64 for small images
        # Large images use file_id for on-demand fetching
        import os
        file_size = os.path.getsize(file_path)

        # Truncate base64 in return value to avoid log spam
        # But keep full version in metadata for WebSocket
        base64_truncated = base64_image[:100] + "...[truncated]" if len(base64_image) > 200 else base64_image

        return {
            "success": True,
            "file_id": file_id,
            "file_path": os.path.basename(file_path),  # Only filename in logs
            "base64": base64_truncated,  # Truncated for log readability
            "chart_type": chart_type,
            "title": title,
            "file_size_bytes": file_size,
            "visualization_metadata": {
                "type": "chart",
                "chart_type": chart_type,
                "title": title,
                "file_id": file_id,  # Include file_id in metadata
                "width": 1000,
                "height": 600,
                "format": "png",
                "base64": base64_image  # Full base64 for WebSocket (if needed by frontend)
            }
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }

@tool
def create_line_plot(
    data: str,
    x_column: str = "x",
    y_column: str = "y",
    title: str = "Line Plot",
    x_label: str = "",
    y_label: str = "",
    save_path: str = "/tmp/line_plot.png"
) -> str:
    """
    Create a line plot from data.
    
    Perfect for: Time series, trends, continuous data
    
    Args:
        data: JSON string with data like '[{"x": 1, "y": 10}, {"x": 2, "y": 20}]'
        x_column: Column name for X axis (default: "x")
        y_column: Column name for Y axis (default: "y")
        title: Plot title
        x_label: X-axis label (default: uses x_column)
        y_label: Y-axis label (default: uses y_column)
        save_path: Where to save the image (default: /tmp/line_plot.png)
        
    Returns:
        JSON string with file info and base64 encoded image
        
    Example:
        data = '[{"position": 1, "gc_content": 0.45}, {"position": 2, "gc_content": 0.52}]'
        create_line_plot(data, "position", "gc_content", "GC Content Distribution")
    """
    try:
        # Parse data
        df = pd.DataFrame(json.loads(data))
        
        # Create figure
        fig, ax = plt.subplots(figsize=(10, 6))
        
        # Plot
        ax.plot(df[x_column], df[y_column], marker='o', linewidth=2, markersize=6)
        
        # Styling
        ax.set_title(title, fontsize=14, fontweight='bold', pad=20)
        ax.set_xlabel(x_label or x_column, fontsize=11)
        ax.set_ylabel(y_label or y_column, fontsize=11)
        ax.grid(True, alpha=0.3)
        
        # Save
        plt.tight_layout()
        plt.savefig(save_path, dpi=150, bbox_inches='tight')
        plt.close()
        
        # Register and get metadata
        result = _save_and_register_plot(save_path, "line", title, f"Line plot showing {y_column} vs {x_column}")
        
        return json.dumps(result, indent=2)
        
    except Exception as e:
        return json.dumps({"success": False, "error": str(e)})

@tool
def create_bar_chart(
    data: str,
    categories: str,  # Column name for categories
    values: str,      # Column name for values
    title: str = "Bar Chart",
    x_label: str = "",
    y_label: str = "",
    horizontal: bool = False,
    save_path: str = "/tmp/bar_chart.png"
) -> str:
    """
    Create a bar chart from categorical data.
    
    Perfect for: Comparing categories, counts, grouped data
    
    Args:
        data: JSON string with data
        categories: Column name for category labels
        values: Column name for bar heights
        title: Chart title
        x_label: X-axis label
        y_label: Y-axis label
        horizontal: If True, create horizontal bars
        save_path: Where to save the image
        
    Returns:
        JSON string with file info and base64 encoded image
    """
    try:
        df = pd.DataFrame(json.loads(data))
        
        fig, ax = plt.subplots(figsize=(10, 6))
        
        if horizontal:
            ax.barh(df[categories], df[values], color=sns.color_palette("husl", len(df)))
            ax.set_ylabel(x_label or categories, fontsize=11)
            ax.set_xlabel(y_label or values, fontsize=11)
        else:
            ax.bar(df[categories], df[values], color=sns.color_palette("husl", len(df)))
            ax.set_xlabel(x_label or categories, fontsize=11)
            ax.set_ylabel(y_label or values, fontsize=11)
        
        ax.set_title(title, fontsize=14, fontweight='bold', pad=20)
        ax.grid(axis='y' if not horizontal else 'x', alpha=0.3)
        
        plt.tight_layout()
        plt.savefig(save_path, dpi=150, bbox_inches='tight')
        plt.close()
        
        result = _save_and_register_plot(save_path, "bar", title, f"Bar chart of {values} by {categories}")
        
        return json.dumps(result, indent=2)
        
    except Exception as e:
        return json.dumps({"success": False, "error": str(e)})

@tool
def create_scatter_plot(
    data: str,
    x_column: str,
    y_column: str,
    title: str = "Scatter Plot",
    color_column: str = None,
    size_column: str = None,
    save_path: str = "/tmp/scatter_plot.png"
) -> str:
    """
    Create a scatter plot to show relationships between variables.
    
    Perfect for: Correlations, clusters, multi-dimensional data
    
    Args:
        data: JSON string with data
        x_column: Column for X axis
        y_column: Column for Y axis
        title: Plot title
        color_column: Optional column to color points by
        size_column: Optional column to size points by
        save_path: Where to save
        
    Returns:
        JSON string with file info and base64 encoded image
    """
    try:
        df = pd.DataFrame(json.loads(data))
        
        fig, ax = plt.subplots(figsize=(10, 6))
        
        # Prepare scatter parameters
        scatter_params = {'alpha': 0.6, 'edgecolors': 'black', 'linewidth': 0.5}
        
        if color_column and color_column in df.columns:
            scatter_params['c'] = df[color_column]
            scatter_params['cmap'] = 'viridis'
        
        if size_column and size_column in df.columns:
            scatter_params['s'] = df[size_column] * 10
        else:
            scatter_params['s'] = 50
        
        scatter = ax.scatter(df[x_column], df[y_column], **scatter_params)
        
        # Add colorbar if using color
        if color_column and color_column in df.columns:
            plt.colorbar(scatter, ax=ax, label=color_column)
        
        ax.set_title(title, fontsize=14, fontweight='bold', pad=20)
        ax.set_xlabel(x_column, fontsize=11)
        ax.set_ylabel(y_column, fontsize=11)
        ax.grid(True, alpha=0.3)
        
        plt.tight_layout()
        plt.savefig(save_path, dpi=150, bbox_inches='tight')
        plt.close()
        
        result = _save_and_register_plot(save_path, "scatter", title, f"Scatter plot: {y_column} vs {x_column}")
        
        return json.dumps(result, indent=2)
        
    except Exception as e:
        return json.dumps({"success": False, "error": str(e)})

@tool
def create_heatmap(
    data: str,
    title: str = "Heatmap",
    x_labels: str = "",
    y_labels: str = "",
    colormap: str = "coolwarm",
    save_path: str = "/tmp/heatmap.png"
) -> str:
    """
    Create a heatmap for matrix data.
    
    Perfect for: Correlation matrices, confusion matrices, grid data
    
    Args:
        data: JSON string with 2D array like '[[1,2,3],[4,5,6],[7,8,9]]'
        title: Heatmap title
        x_labels: Comma-separated X-axis labels (optional)
        y_labels: Comma-separated Y-axis labels (optional)
        colormap: Color scheme (coolwarm, viridis, RdYlGn, etc.)
        save_path: Where to save
        
    Returns:
        JSON string with file info and base64 encoded image
    """
    try:
        matrix_data = np.array(json.loads(data))
        
        fig, ax = plt.subplots(figsize=(10, 8))
        
        # Create heatmap
        sns.heatmap(
            matrix_data,
            annot=True,
            fmt='.2f',
            cmap=colormap,
            cbar=True,
            square=True,
            ax=ax,
            xticklabels=x_labels.split(',') if x_labels else 'auto',
            yticklabels=y_labels.split(',') if y_labels else 'auto'
        )
        
        ax.set_title(title, fontsize=14, fontweight='bold', pad=20)
        
        plt.tight_layout()
        plt.savefig(save_path, dpi=150, bbox_inches='tight')
        plt.close()
        
        result = _save_and_register_plot(save_path, "heatmap", title, f"Heatmap visualization: {title}")
        
        return json.dumps(result, indent=2)
        
    except Exception as e:
        return json.dumps({"success": False, "error": str(e)})

@tool
def create_distribution_plot(
    data: str,
    column: str,
    title: str = "Distribution Plot",
    plot_type: str = "histogram",  # histogram, kde, or both
    bins: int = 30,
    save_path: str = "/tmp/distribution_plot.png"
) -> str:
    """
    Create a distribution plot to show data distribution.
    
    Perfect for: Statistical analysis, data exploration, quality control
    
    Args:
        data: JSON string with data
        column: Column name to plot distribution
        title: Plot title
        plot_type: Type of plot (histogram, kde, or both)
        bins: Number of bins for histogram
        save_path: Where to save
        
    Returns:
        JSON string with file info and base64 encoded image
    """
    try:
        df = pd.DataFrame(json.loads(data))
        
        fig, ax = plt.subplots(figsize=(10, 6))
        
        if plot_type == "histogram":
            ax.hist(df[column], bins=bins, edgecolor='black', alpha=0.7)
        elif plot_type == "kde":
            df[column].plot(kind='kde', ax=ax, linewidth=2)
        else:  # both
            ax.hist(df[column], bins=bins, edgecolor='black', alpha=0.5, density=True, label='Histogram')
            df[column].plot(kind='kde', ax=ax, linewidth=2, color='red', label='KDE')
            ax.legend()
        
        ax.set_title(title, fontsize=14, fontweight='bold', pad=20)
        ax.set_xlabel(column, fontsize=11)
        ax.set_ylabel('Frequency' if plot_type == 'histogram' else 'Density', fontsize=11)
        ax.grid(True, alpha=0.3)
        
        plt.tight_layout()
        plt.savefig(save_path, dpi=150, bbox_inches='tight')
        plt.close()
        
        result = _save_and_register_plot(save_path, "distribution", title, f"Distribution of {column}")
        
        return json.dumps(result, indent=2)
        
    except Exception as e:
        return json.dumps({"success": False, "error": str(e)})

# Helper function to mark a tool as visualization tool
VISUALIZATION_TOOLS = {
    'create_line_plot',
    'create_bar_chart', 
    'create_scatter_plot',
    'create_heatmap',
    'create_distribution_plot'
}

def is_visualization_tool(tool_name: str) -> bool:
    """Check if a tool is a visualization tool"""
    return tool_name in VISUALIZATION_TOOLS
