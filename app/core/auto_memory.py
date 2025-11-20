import time
from collections import deque


class AutoMemory:
    """Lightweight memory that automatically tracks agent activities"""
    
    def __init__(self):
        self.task_history = deque(maxlen=50)      # Recent tasks
        self.tool_usage = {}                      # Tool usage statistics
        self.success_patterns = {}                # Successful task patterns
        self.error_history = deque(maxlen=20)     # Recent errors
        self.agent_performance = {}               # Agent performance metrics
        
    def record_task(self, agent_name: str, task: str, result: str, success: bool, duration: float):
        """Automatically record task execution"""
        self.task_history.append({
            'agent': agent_name,
            'task': task[:100],
            'success': success,
            'duration': duration,
            'timestamp': time.time()
        })
        
        # Update agent performance
        if agent_name not in self.agent_performance:
            self.agent_performance[agent_name] = {'total': 0, 'success': 0, 'avg_duration': 0}
        
        stats = self.agent_performance[agent_name]
        stats['total'] += 1
        if success:
            stats['success'] += 1
        
        # Update average duration
        old_avg = stats['avg_duration']
        stats['avg_duration'] = (old_avg * (stats['total'] - 1) + duration) / stats['total']
        
    def record_tool_use(self, tool_name: str, success: bool):
        """Record tool usage"""
        if tool_name not in self.tool_usage:
            self.tool_usage[tool_name] = {'uses': 0, 'success': 0}
        
        self.tool_usage[tool_name]['uses'] += 1
        if success:
            self.tool_usage[tool_name]['success'] += 1
    
    def get_similar_tasks(self, task: str, limit: int = 3):
        """Find similar successful tasks"""
        keywords = set(task.lower().split())
        matches = []
        
        for hist in self.task_history:
            if hist['success']:
                task_keywords = set(hist['task'].lower().split())
                score = len(keywords & task_keywords)
                if score > 0:
                    matches.append((score, hist))
        
        matches.sort(key=lambda x: x[0], reverse=True)
        return [m[1] for m in matches[:limit]]
    
    def get_best_agent_for_task(self, task: str):
        """Suggest best agent based on performance"""
        similar_tasks = self.get_similar_tasks(task)
        if similar_tasks:
            # Count which agents succeeded most
            agent_counts = {}
            for t in similar_tasks:
                agent = t['agent']
                agent_counts[agent] = agent_counts.get(agent, 0) + 1
            
            # Return agent with most successes
            return max(agent_counts.items(), key=lambda x: x[1])[0] if agent_counts else None
        return None


# Global auto memory instance
auto_memory = AutoMemory()




