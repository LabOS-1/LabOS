import os
import re
import requests
import subprocess
import json
import time
import sys
from pathlib import Path
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

# Smolagents imports for proper message handling
from smolagents import ChatMessage, MessageRole

# --- Knowledge Base System ---
class KnowledgeBase:
    """Knowledge base system - store and retrieve successful thinking templates"""

    def __init__(self, gemini_model=None):
        self.templates = []
        self.vectorizer = TfidfVectorizer(stop_words='english', max_features=1000)
        self.template_vectors = None
        self.knowledge_file = Path("data/outputs/agent_knowledge_base.json")
        self.gemini_model = gemini_model  # 添加 Gemini 模型支持

        # Load existing knowledge base
        self.load_knowledge_base()

    def summarize_reasoning_process(self, question_text, detailed_reasoning, correct_answer):
        """使用LLM总结推理过程的关键步骤"""
        summarization_prompt = f"""Please summarize the key reasoning steps from the following detailed analysis.
Focus on the essential logical steps and principles that led to the successful solution, without revealing the specific answer.

Task/Question: {question_text}

Detailed Reasoning Process:
{detailed_reasoning}

Please provide a concise summary of 4-5 key reasoning principles and methodological approaches that were crucial for solving this type of problem. Do not include the final answer.

Key Reasoning Summary:"""

        try:
            print("🧠 调用模型进行推理总结...")

            # Use correct message format for smolagents
            response = self.gemini_model([{"role": "user", "content": summarization_prompt}])

            # Handle different response formats
            if hasattr(response, 'content'):
                summary = response.content
            elif isinstance(response, dict) and 'content' in response:
                summary = response['content']
            elif isinstance(response, str):
                summary = response
            else:
                summary = str(response)

            # Clean and validate the summary
            if summary and isinstance(summary, str):
                summary = summary.strip()
                # Remove common non-informative starts
                if summary.lower().startswith(('key reasoning summary:', 'summary:', 'the key reasoning')):
                    lines = summary.split('\n')
                    summary = '\n'.join(lines[1:]).strip() if len(lines) > 1 else summary

                # Ensure it's informative (not just generic text)
                if len(summary) > 50 and 'systematic analysis' not in summary.lower():
                    # Limit length
                    if len(summary) > 800:
                        summary = summary[:800] + "..."
                    print(f"✅ Successfully generated reasoning summary: {summary[:100]}...")
                    return summary
                else:
                    print(f"⚠️ Model-generated summary too generic or short: {summary[:100]}")
                    return self._generate_manual_summary(question_text, detailed_reasoning)
            else:
                print(f"⚠️ 意外的模型响应类型: {type(summary)}")
                return self._generate_manual_summary(question_text, detailed_reasoning)

        except Exception as e:
            print(f"❌ Reasoning summary failed: {str(e)}")
            import traceback
            print(f"   详细错误: {traceback.format_exc()}")
            return self._generate_manual_summary(question_text, detailed_reasoning)

    def _generate_manual_summary(self, question_text, detailed_reasoning):
        """Manually generate reasoning summary as fallback"""
        try:
            # Extract some key concepts from the question and reasoning
            question_lower = question_text.lower()
            reasoning_lower = detailed_reasoning.lower() if detailed_reasoning else ""

            # Identify domain-specific approaches
            if any(term in question_lower for term in ['data', 'analysis', 'csv', 'plot', 'graph']):
                return "Applied systematic data analysis with visualization and statistical interpretation approaches."
            elif any(term in question_lower for term in ['code', 'script', 'programming', 'function']):
                return "Used systematic programming approach with modular design and error handling principles."
            elif any(term in question_lower for term in ['search', 'research', 'find', 'information']):
                return "Applied comprehensive information retrieval with source verification and synthesis methods."
            elif any(term in question_lower for term in ['biomedical', 'biology', 'medical', 'health']):
                return "Applied biomedical reasoning with evidence-based analysis and scientific methodology."
            else:
                return "Applied systematic problem-solving approach with logical reasoning and evidence-based analysis."
        except:
            return "Applied systematic problem-solving approach with methodical analysis."

    def add_template(self, task_description, thought_process, solution_outcome, domain):
        """Add successful thinking template to knowledge base (using LLM summary, not storing specific answers)"""

        # 使用LLM总结关键推理步骤
        print("🧠 正在总结推理过程...")
        key_reasoning = self.summarize_reasoning_process(task_description, thought_process, solution_outcome)

        template = {
            'task': task_description,
            'key_reasoning': key_reasoning,  # 存储总结的关键推理步骤
            'domain': domain,
            'keywords': self.extract_keywords(task_description),
            'timestamp': time.strftime("%Y-%m-%d %H:%M:%S")
        }

        self.templates.append(template)

        # 重新计算向量
        self.rebuild_vectors()

        # 限制知识库大小
        if len(self.templates) > 1000:
            self.templates = self.templates[-1000:]  # 保留最新1000个
            self.rebuild_vectors()

        # 保存到文件
        self.save_knowledge_base()

        print(f"💾 知识库新增模板（已总结），总数: {len(self.templates)}")

        # 返回成功状态
        return {
            "success": True,
            "message": f"Template added successfully. Total templates: {len(self.templates)}",
            "template_id": len(self.templates) - 1
        }

    def extract_keywords(self, text):
        """提取关键词 - 使用 Gemini 模型或回退到静态关键词"""

        # 如果有 Gemini 模型，使用 AI 进行关键词提取
        if self.gemini_model:
            try:
                keyword_prompt = f"""Extract 3-8 most important keywords from the following text, focusing on technical, scientific, medical, biological, data analysis, programming, and related professional terms.

Please return only keywords, separated by commas, without any other explanations or punctuation.

Text: {text}

Keywords:"""

                response = self.gemini_model([{"role": "user", "content": keyword_prompt}])

                # 处理响应
                if hasattr(response, 'content'):
                    keywords_str = response.content.strip()
                elif isinstance(response, dict) and 'content' in response:
                    keywords_str = response['content'].strip()
                elif isinstance(response, str):
                    keywords_str = response.strip()
                else:
                    keywords_str = str(response).strip()

                # 解析关键词
                keywords = [kw.strip().lower() for kw in keywords_str.split(',')]
                keywords = [kw for kw in keywords if kw and len(kw) > 2]  # 过滤空白和太短的词

                if keywords:
                    return keywords

            except Exception as e:
                print(f"⚠️ Gemini 关键词提取失败，回退到静态方法: {str(e)}")

        # 回退到原始的静态关键词方法
        tech_keywords = [
            # 通用技术关键词
            'data', 'analysis', 'code', 'script', 'programming', 'algorithm',
            'visualization', 'plot', 'chart', 'graph', 'statistics', 'model',
            'database', 'search', 'information', 'literature', 'paper',

            # 生物学通用术语
            'biomedical', 'biology', 'medical', 'research', 'scientific',
            'bioinformatics', 'computational', 'experimental', 'clinical',

            # 基于 Biomni 工具分类的专业术语
            'molecular_biology', 'molecular', 'cell_biology', 'cellular',
            'genetics', 'genetic', 'genomics', 'genome', 'genomic',
            'biochemistry', 'biochemical', 'immunology', 'immune', 'immunological',
            'microbiology', 'microbiological', 'microbial', 'bacterial',
            'cancer_biology', 'cancer', 'oncology', 'tumor', 'malignancy',
            'pathology', 'pathological', 'disease', 'disorder',
            'pharmacology', 'pharmacological', 'drug', 'therapeutic', 'treatment',
            'physiology', 'physiological', 'function', 'metabolism',
            'systems_biology', 'systems', 'network', 'pathway',
            'synthetic_biology', 'synthetic', 'engineering', 'design',
            'bioengineering', 'biomedical_engineering', 'biotechnology',
            'biophysics', 'biophysical', 'structural', 'protein', 'enzyme',

            # 实验技术和方法
            'sequencing', 'pcr', 'microscopy', 'imaging', 'assay',
            'chromatography', 'electrophoresis', 'blotting', 'culture',
            'transfection', 'transformation', 'cloning', 'expression',
            'purification', 'crystallization', 'spectroscopy',

            # 数据分析和计算
            'machine_learning', 'deep_learning', 'neural_network',
            'classification', 'clustering', 'regression', 'prediction',
            'simulation', 'modeling', 'optimization', 'annotation'
        ]

        text_lower = text.lower()
        found_keywords = [kw for kw in tech_keywords if kw in text_lower]
        return found_keywords

    def rebuild_vectors(self):
        """重建向量表示"""
        if len(self.templates) == 0:
            return

        # 组合任务文本、关键推理和关键词
        texts = []
        for t in self.templates:
            # 处理新旧格式兼容性
            reasoning = t.get('key_reasoning', t.get('thought_process', ''))
            text = f"{t['task']} {reasoning} {' '.join(t['keywords'])}"
            texts.append(text)

        try:
            self.template_vectors = self.vectorizer.fit_transform(texts)
        except Exception as e:
            print(f"⚠️ 向量重建失败: {str(e)}")
            self.template_vectors = None

    def retrieve_similar_templates(self, task_description, top_k=3):
        """检索相似的思维模板"""
        if len(self.templates) == 0 or self.template_vectors is None:
            return []

        try:
            # 向量化当前任务
            task_vector = self.vectorizer.transform([task_description])

            # 计算相似度
            similarities = cosine_similarity(task_vector, self.template_vectors).flatten()

            # 获取top_k个最相似的模板
            top_indices = np.argsort(similarities)[::-1][:top_k]

            similar_templates = []
            for idx in top_indices:
                if similarities[idx] > 0.1:  # 相似度阈值
                    template = self.templates[idx].copy()
                    template['similarity'] = similarities[idx]
                    similar_templates.append(template)

            print(f"🔍 找到 {len(similar_templates)} 个相似模板")
            return similar_templates

        except Exception as e:
            print(f"⚠️ 模板检索失败: {str(e)}")
            return []

    def search_templates_by_keyword(self, keyword):
        """按关键词搜索模板"""
        matching_templates = []
        keyword_lower = keyword.lower()

        for template in self.templates:
            # 在任务描述、关键推理和关键词中搜索
            if (keyword_lower in template['task'].lower() or
                keyword_lower in template.get('key_reasoning', '').lower() or
                keyword_lower in ' '.join(template['keywords']).lower()):
                matching_templates.append(template)

        print(f"🔍 关键词 '{keyword}' 匹配到 {len(matching_templates)} 个模板")
        return matching_templates

    def save_knowledge_base(self):
        """保存知识库到文件"""
        try:
            # 确保输出目录存在
            self.knowledge_file.parent.mkdir(parents=True, exist_ok=True)

            with open(self.knowledge_file, 'w', encoding='utf-8') as f:
                json.dump(self.templates, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"⚠️ 保存知识库失败: {str(e)}")

    def load_knowledge_base(self):
        """从文件加载知识库"""
        try:
            if self.knowledge_file.exists():
                with open(self.knowledge_file, 'r', encoding='utf-8') as f:
                    self.templates = json.load(f)

                # Rebuild vectors
                self.rebuild_vectors()

                print(f"✅ Successfully loaded knowledge base with {len(self.templates)} templates")
            else:
                print("📚 Knowledge base file does not exist, starting from blank")
        except Exception as e:
            print(f"⚠️ Failed to load knowledge base: {str(e)}")
            self.templates = []
