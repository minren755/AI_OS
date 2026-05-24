"""
信息完整性检查器 - 方案B实现
"""
import re
from typing import List, Dict, Tuple


class InfoChecker:
    """检查需求信息完整性，生成交互问题"""
    
    # 关键信息类型及其检查规则
    INFO_RULES = {
        "公司业务": {
            "keywords": ["业务", "服务", "产品", "做什么", "主营业务", "核心业务", "提供"],
            "questions": [
                "请问公司主要业务是什么？",
                "公司提供哪些核心服务？"
            ]
        },
        "公司特色": {
            "keywords": ["特色", "优势", "亮点", "不同", "独特", "竞争力"],
            "questions": [
                "公司有什么独特优势或特色？",
                "相比同行有什么亮点？"
            ]
        },
        "目标用户": {
            "keywords": ["用户", "客户", "受众", "目标", "人群", "面向"],
            "questions": [
                "目标用户群体是谁？",
                "主要服务哪些客户？"
            ]
        },
        "设计风格": {
            "keywords": ["风格", "色调", "颜色", "设计", "视觉", "简约", "科技"],
            "questions": [
                "希望什么设计风格？（如：简约、科技感、商务等）",
                "有偏好的颜色或色调吗？"
            ]
        },
        "功能需求": {
            "keywords": ["功能", "模块", "页面", "交互", "按钮", "表单"],
            "questions": [
                "需要哪些具体功能？",
                "有哪些必填内容或模块？"
            ]
        },
        "联系方式": {
            "keywords": ["联系", "电话", "邮箱", "地址", "微信"],
            "questions": [
                "需要展示哪些联系方式？",
                "公司地址和联系电话是什么？"
            ]
        }
    }
    
    def __init__(self, min_info_count: int = 2):
        """
        Args:
            min_info_count: 最少需要包含的信息类型数量
        """
        self.min_info_count = min_info_count
    
    def check_completeness(self, topic: str) -> Tuple[bool, List[str]]:
        """
        检查信息完整性
        
        Returns:
            (is_complete, missing_info_types)
        """
        found_info_types = set()
        
        # 检查每种信息类型
        for info_type, rule in self.INFO_RULES.items():
            for keyword in rule["keywords"]:
                if keyword in topic:
                    found_info_types.add(info_type)
                    break
        
        # 判断是否完整
        is_complete = len(found_info_types) >= self.min_info_count
        
        # 找出缺失的信息类型
        missing = [t for t in self.INFO_RULES.keys() if t not in found_info_types]
        
        return is_complete, missing
    
    def generate_questions(self, missing_types: List[str], max_questions: int = 3) -> List[str]:
        """
        根据缺失信息生成问题
        
        Args:
            missing_types: 缺失的信息类型列表
            max_questions: 最多生成几个问题
        """
        questions = []
        
        for info_type in missing_types[:max_questions]:
            rule = self.INFO_RULES.get(info_type)
            if rule and rule["questions"]:
                questions.append(rule["questions"][0])
        
        return questions
    
    def format_prompt_for_user(self, questions: List[str]) -> str:
        """格式化提示语"""
        if not questions:
            return ""
        
        prompt = "为了更好地完成任务，请补充以下信息：\n\n"
        for i, q in enumerate(questions, 1):
            prompt += f"{i}. {q}\n"
        
        prompt += "\n请回复以上问题，或直接说「继续」跳过。"
        return prompt


# 便捷函数
def check_and_ask(topic: str) -> Dict:
    """
    检查信息完整性并生成问题
    
    Returns:
        {
            "need_input": bool,
            "missing": List[str],
            "questions": List[str],
            "prompt": str
        }
    """
    checker = InfoChecker()
    is_complete, missing = checker.check_completeness(topic)
    
    if is_complete:
        return {
            "need_input": False,
            "missing": [],
            "questions": [],
            "prompt": ""
        }
    
    questions = checker.generate_questions(missing)
    prompt = checker.format_prompt_for_user(questions)
    
    return {
        "need_input": True,
        "missing": missing,
        "questions": questions,
        "prompt": prompt
    }