"""
依赖推断模块 - P1
基于任务描述自动推断依赖关系
"""
from typing import List, Dict, Tuple
import re


class DependencyInferrer:
    """依赖推断引擎"""
    
    # 依赖触发关键词（左侧任务依赖右侧类型的任务）
    DEPENDENCY_TRIGGERS = {
        # 测试类依赖开发类
        "测试": ["开发", "实现", "编写", "设计"],
        "验证": ["开发", "实现"],
        "调试": ["开发", "实现"],
        
        # 集成类依赖前端任务
        "集成": ["开发", "实现", "前端", "接口"],
        "部署": ["开发", "测试", "构建"],
        
        # 使用类依赖产出类
        "使用": ["创建", "生成", "设计"],
        "读取": ["创建", "生成", "编写"],
        "调用": ["开发", "实现", "接口"],
        
        # 基于类依赖设计类
        "基于": ["设计", "方案"],
        "参考": ["设计", "文档"],
    }
    
    # 产出关键词（这些任务通常被其他任务依赖）
    OUTPUT_KEYWORDS = [
        "创建", "生成", "输出", "产出", "编写", "设计",
        "开发", "实现", "构建", "配置"
    ]
    
    # 文件产出模式
    FILE_OUTPUT_PATTERN = re.compile(
        r'(创建|生成|输出|编写).*?([a-zA-Z0-9_\-]+\.(py|js|html|css|json|yaml|md|txt|sql))'
    )
    
    # API产出模式
    API_OUTPUT_PATTERN = re.compile(
        r'(开发|实现|创建).*?(API|api|接口).*?(/[/a-zA-Z0-9_\-]+)'
    )
    
    def infer(self, tasks: List) -> List:
        """推断任务依赖关系"""
        
        # 1. 分析每个任务的产出
        task_outputs = self._analyze_outputs(tasks)
        
        # 2. 分析每个任务的依赖需求
        task_needs = self._analyze_needs(tasks)
        
        # 3. 匹配需求和产出，建立依赖
        for i, task in enumerate(tasks):
            inferred_deps = self._match_needs_to_outputs(
                task_needs[i], 
                task_outputs, 
                tasks, 
                i
            )
            
            # 合并推断依赖和原有依赖
            existing_deps = set(task.dependencies)
            new_deps = set(inferred_deps)
            task.dependencies = list(existing_deps | new_deps)
        
        return tasks
    
    def _analyze_outputs(self, tasks: List) -> Dict[int, Dict]:
        """分析每个任务的产出"""
        outputs = {}
        
        for i, task in enumerate(tasks):
            output = {
                "files": [],
                "apis": [],
                "features": [],
                "keywords": []
            }
            
            desc = task.description.lower() + task.name.lower()
            
            # 提取文件产出
            file_matches = self.FILE_OUTPUT_PATTERN.findall(task.description)
            for match in file_matches:
                output["files"].append(match[1])
            
            # 提取API产出
            api_matches = self.API_OUTPUT_PATTERN.findall(task.description)
            for match in api_matches:
                output["apis"].append(match[2])
            
            # 提取功能关键词
            for kw in self.OUTPUT_KEYWORDS:
                if kw in desc:
                    output["keywords"].append(kw)
            
            # 提取功能名称（简化：任务名去掉常见后缀）
            feature_name = task.name
            for suffix in ["开发", "实现", "设计", "测试", "编写", "创建"]:
                feature_name = feature_name.replace(suffix, "")
            if feature_name and len(feature_name) > 2:
                output["features"].append(feature_name.strip())
            
            outputs[i] = output
        
        return outputs
    
    def _analyze_needs(self, tasks: List) -> Dict[int, Dict]:
        """分析每个任务的依赖需求"""
        needs = {}
        
        for i, task in enumerate(tasks):
            need = {
                "files": [],
                "apis": [],
                "features": [],
                "trigger_keywords": []
            }
            
            desc = task.description.lower() + task.name.lower()
            
            # 提取文件需求（"读取X", "使用X"）
            file_need_pattern = re.compile(r'(读取|使用|调用|基于).*?([a-zA-Z0-9_\-]+\.(py|js|html|css|json|yaml|md|sql))')
            file_matches = file_need_pattern.findall(task.description)
            for match in file_matches:
                need["files"].append(match[1])
            
            # 提取API需求
            api_need_pattern = re.compile(r'(调用|使用|请求).*?(API|api|接口).*?(/[/a-zA-Z0-9_\-]+)')
            api_matches = api_need_pattern.findall(task.description)
            for match in api_matches:
                need["apis"].append(match[2])
            
            # 提取触发关键词
            for trigger, _ in self.DEPENDENCY_TRIGGERS.items():
                if trigger in desc:
                    need["trigger_keywords"].append(trigger)
            
            # 提取功能需求
            feature_need_pattern = re.compile(r'(测试|验证).*?([a-zA-Z0-9_\-\u4e00-\u9fa5]+)')
            feature_matches = feature_need_pattern.findall(task.name + task.description)
            for match in feature_matches:
                feature = match[1].replace("功能", "").strip()
                if feature and len(feature) > 2:
                    need["features"].append(feature)
            
            needs[i] = need
        
        return needs
    
    def _match_needs_to_outputs(
        self, 
        need: Dict, 
        outputs: Dict[int, Dict], 
        tasks: List,
        current_idx: int
    ) -> List[str]:
        """匹配需求和产出"""
        dependencies = []
        
        # 文件匹配
        for file in need["files"]:
            for j, output in outputs.items():
                if j < current_idx and file in output["files"]:
                    dependencies.append(tasks[j].id)
        
        # API匹配
        for api in need["apis"]:
            for j, output in outputs.items():
                if j < current_idx and api in output["apis"]:
                    dependencies.append(tasks[j].id)
        
        # 功能匹配
        for feature in need["features"]:
            for j, output in outputs.items():
                if j < current_idx:
                    for out_feature in output["features"]:
                        if feature in out_feature or out_feature in feature:
                            dependencies.append(tasks[j].id)
        
        # 关键词触发匹配
        for trigger in need["trigger_keywords"]:
            target_keywords = self.DEPENDENCY_TRIGGERS.get(trigger, [])
            for j, output in outputs.items():
                if j < current_idx:
                    for kw in output["keywords"]:
                        if kw in target_keywords:
                            dependencies.append(tasks[j].id)
                            break
        
        # 去重
        return list(set(dependencies))


def infer_dependencies(tasks: List) -> List:
    """便捷函数"""
    inferrer = DependencyInferrer()
    return inferrer.infer(tasks)