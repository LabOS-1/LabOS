"""
Prompt Template Loader

This module handles loading and rendering agent prompts:
- Load agent prompts from YAML files
- Load custom prompt templates
- Render Jinja2 templates with variables
- Provide template variables for agents
"""

import yaml
import os
from jinja2 import Template
from pathlib import Path


def load_agent_prompts():
    """Load agent_prompts.yaml configuration file.

    Returns:
        Dictionary containing agent prompt configurations
    """
    try:
        # Get app directory by navigating up from app/core/engines/smolagents/agents
        app_dir = Path(__file__).resolve().parents[4]
        agent_prompts_path = app_dir / "config" / "prompts" / "agent_prompts.yaml"

        with open(agent_prompts_path, 'r', encoding='utf-8') as stream:
            return yaml.safe_load(stream)
    except Exception as e:
        print(f"❌ Error loading agent prompts: {e}")
        return None


def load_custom_prompts(mode='deep'):
    """Load LabOS custom prompt templates.

    Args:
        mode: 'deep' for full workflow or 'fast' for quick responses (default: 'deep')

    Can choose between versions via LABOS_PROMPT_VERSION environment variable:
    - 'v1' or unset: LabOS_prompt_bioml.yaml (original, detailed)
    - 'v2': LabOS_prompt_bioml_v2.yaml (optimized, concise)
    - 'v3': LabOS_prompt_bioml_v3.yaml (v2 + GenomeBench MCQ enhancement)
    - mode='fast': LabOS_prompt_fast_mode.yaml (lightweight, no tools)

    Returns:
        Dictionary containing custom prompt templates
    """
    # Fast mode uses dedicated lightweight prompt
    if mode == 'fast':
        prompt_filename = "LabOS_prompt_fast_mode.yaml"
    else:
        # Deep mode: check environment variable for prompt version
        prompt_version = os.environ.get('LABOS_PROMPT_VERSION', 'v1')

        if prompt_version == 'v3':
            prompt_filename = "LabOS_prompt_bioml_v3.yaml"
        elif prompt_version == 'v2':
            prompt_filename = "LabOS_prompt_bioml_v2.yaml"
        else:
            prompt_filename = "LabOS_prompt_bioml.yaml"

    try:
        # Get app directory by navigating up from app/core/engines/smolagents/agents
        app_dir = Path(__file__).resolve().parents[4]
        prompt_templates_path = app_dir / "config" / "prompts" / prompt_filename

        with open(prompt_templates_path, 'r', encoding='utf-8') as stream:
            custom_prompts = yaml.safe_load(stream)

        if mode == 'fast':
            print(f"⚡ Fast Mode prompts loaded: {prompt_templates_path}")
        else:
            prompt_version = os.environ.get('LABOS_PROMPT_VERSION', 'v1')
            print(f"✅ Custom prompts loaded ({prompt_version}): {prompt_templates_path}")

        return custom_prompts
    except FileNotFoundError:
        print(f"📋 Custom prompts not found: {prompt_filename}")
        # Fallback to v1 if v2 not found
        if prompt_version == 'v2':
            print(f"⚠️ Falling back to v1 prompt")
            return load_custom_prompts_v1()
        return None
    except Exception as e:
        print(f"⚠️ Error loading custom prompts: {str(e)}")
        return None


def load_custom_prompts_v1():
    """Fallback loader for v1 prompts."""
    try:
        # Get app directory by navigating up from app/core/engines/smolagents/agents
        app_dir = Path(__file__).resolve().parents[4]
        prompt_templates_path = app_dir / "config" / "prompts" / "LabOS_prompt_bioml.yaml"

        with open(prompt_templates_path, 'r', encoding='utf-8') as stream:
            custom_prompts = yaml.safe_load(stream)
        print(f"✅ Custom prompts loaded (v1 fallback): {prompt_templates_path}")
        return custom_prompts
    except Exception as e:
        print(f"❌ Failed to load v1 fallback: {str(e)}")
        return None


def render_prompt_templates(templates, variables):
    """Render Jinja2 templates with provided variables.

    Args:
        templates: Dictionary of template content (str or nested dict)
        variables: Dictionary of variables to use in rendering

    Returns:
        Dictionary of rendered templates
    """
    rendered = {}

    for key, template_content in templates.items():
        if isinstance(template_content, str):
            template = Template(template_content)
            rendered[key] = template.render(**variables)
        elif isinstance(template_content, dict):
            rendered_sub_templates = {}
            for sub_key, sub_content in template_content.items():
                if isinstance(sub_content, str):
                    template = Template(sub_content)
                    rendered_sub_templates[sub_key] = template.render(**variables)
                else:
                    rendered_sub_templates[sub_key] = sub_content
            rendered[key] = rendered_sub_templates
        else:
            rendered[key] = template_content

    return rendered


def get_template_variables(managed_agents, tools):
    """Get template variables for Jinja2 rendering.

    Args:
        managed_agents: Dictionary of managed agent instances
        tools: Dictionary or list of available tools

    Returns:
        Dictionary of template variables
    """
    return {
        'code_block_opening_tag': '<code>',
        'code_block_closing_tag': '</code>',
        'custom_instructions': '',
        'authorized_imports': ', '.join([
            "time", "datetime", "os", "sys", "json", "csv", "pickle", "pathlib",
            "math", "statistics", "random", "numpy", "pandas",
            "collections", "itertools", "functools", "operator",
            "typing", "dataclasses", "enum", "xml", "xml.etree", "xml.etree.ElementTree",
            "requests", "urllib", "urllib.parse", "http", "re", "unicodedata", "string"
        ]),
        'managed_agents': managed_agents,
        'tools': {tool.name if hasattr(tool, 'name') else str(tool): tool for tool in tools} if isinstance(tools, list) else tools
    }
