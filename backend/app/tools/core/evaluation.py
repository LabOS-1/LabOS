"""
Evaluation Tools - Task evaluation tools
Use critic agent to evaluate task completion quality
"""

from smolagents import tool


@tool
def evaluate_with_critic(task_description: str, current_result: str, expected_outcome: str = "") -> str:
    """Use the critic agent to evaluate task completion and recommend improvements.
    
    Args:
        task_description: Original task description
        current_result: Current result or output achieved
        expected_outcome: Expected outcome (optional)
        
    Returns:
        Critic evaluation with tool creation recommendations
    """
    # Import here to avoid circular dependency
    from app.core.engines.smolagents.labos_engine import critic_agent
    
    try:
        # Enhanced prompt with ML performance standards
        evaluation_prompt = f"""
Evaluate ML model task completion with focus on PERFORMANCE METRICS:

TASK: {task_description}
FULL RESULT: {current_result[:1500]}  # Include more context for performance analysis
EXPECTED: {expected_outcome if expected_outcome else "High-performance ML model with good correlation scores"}

Provide evaluation focusing on ACTUAL PERFORMANCE:
1. status: EXCELLENT/SATISFACTORY/NEEDS_IMPROVEMENT/POOR (based on performance metrics, not just completion)
2. quality_score: 1-10 (heavily weight actual performance metrics)
3. gaps: performance issues and missing optimizations (max 3)
4. should_create_tool: true/false (recommend iteration tools for poor performance)
5. recommended_tool: if performance is poor, suggest optimization tools
6. performance_analysis: brief analysis of the numerical results

Be critical of poor performance. Completion ≠ Success.
"""
        
        critic_response = critic_agent.run(evaluation_prompt)
        return critic_response
        
    except Exception as e:
        return f"Error in critic evaluation: {str(e)}"

