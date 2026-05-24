"""
AI_OS讨论引擎 - 直接调用LLM API
"""
import json
import asyncio
from typing import Dict, List, Optional
from dataclasses import dataclass, field
from datetime import datetime
import httpx
import yaml
from pathlib import Path


@dataclass
class AgentResponse:
    """Agent响应结构"""
    content: str
    satisfied: bool = False
    next_speakers: List[str] = field(default_factory=list)
    concerns: List[str] = field(default_factory=list)
    skipped: bool = False


@dataclass
class DiscussionConfig:
    """讨论配置"""
    agent_configs: Dict[str, str] = field(default_factory=dict)
    max_rounds: int = 5
    context_window: int = 2  # 保留最近N轮摘要
    skip_signals: List[str] = field(default_factory=lambda: [
        "跳过", "无需补充", "无意见", "同意上述", "pass", ""
    ])


class DiscussionEngine:
    """动态讨论引擎"""
    
    DEFAULT_ORDER = ["CEO", "CFO", "CTO", "CMO"]
    
    def __init__(self, config: DiscussionConfig = None):
        self.config = config or DiscussionConfig()
        self.history: List[Dict[str, AgentResponse]] = []
        self.agent_state: Dict[str, Dict] = {}
        self.llm_configs: Dict[str, Dict] = {}
        self._init_configs()
    
    def _init_configs(self):
        """加载各Agent的LLM配置 - 使用统一的环境变量配置"""
        import os
        from ..config.settings import get_llm_config
        
        llm_config = get_llm_config()
        
        if not llm_config.get('api_key'):
            print("未找到API配置")
            return
        
        # 所有Agent使用相同的配置
        for agent in self.DEFAULT_ORDER:
            self.llm_configs[agent] = llm_config
            self.agent_state[agent] = {
                "active": True,
                "satisfied": False,
                "speak_count": 0,
                "skip_count": 0
            }
    
    async def run(self, topic: str) -> Dict:
        """执行完整讨论"""
        self._topic = topic  # 保存议题供日志使用
        print(f"\n{'='*50}")
        print(f"议题: {topic}")
        print(f"{'='*50}\n")
        
        # 检查配置
        available = [a for a, c in self.llm_configs.items() if c]
        if not available:
            print("无可用的Agent配置")
            return {"总轮数": 0, "共识达成": False}
        
        print(f"参与Agent: {available}\n")
        
        # 监控回调：讨论开始
        if hasattr(self, 'on_event') and callable(self.on_event):
            self.on_event({"type": "start", "topic": topic, "agents": available})
        
        for round_num in range(1, self.config.max_rounds + 1):
            print(f"\n--- Round {round_num} ---")
            
            # 监控回调：轮次开始
            if hasattr(self, 'on_event') and callable(self.on_event):
                self.on_event({"type": "round_start", "round": round_num})
            
            speakers = self._determine_speakers()
            if not speakers:
                print("所有Agent已满意，提前结束")
                break
            
            round_outputs = await self._run_round(speakers, topic, round_num)
            self.history.append(round_outputs)
            
            # 监控回调：轮次结束
            if hasattr(self, 'on_event') and callable(self.on_event):
                self.on_event({"type": "round_end", "round": round_num})
            
            if self._check_consensus():
                print("\n✓ 达成共识!")
                if hasattr(self, 'on_event') and callable(self.on_event):
                    self.on_event({"type": "consensus"})
                break
        
        # CEO最终总结
        await self._ceo_summary(topic)
        
        result = self._summarize()
        self._save_log(result)
        return result
    
    def _save_log(self, result: Dict):
        """保存讨论日志"""
        PROJECT_ROOT = Path(__file__).parent.parent.parent
        log_file = PROJECT_ROOT / "logs" / f"discussion_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        log_file.parent.mkdir(exist_ok=True)
        
        with open(log_file, "w") as f:
            json.dump(result, f, ensure_ascii=False, indent=2)
        
        # 同时保存可读的文本日志
        text_log = log_file.with_suffix(".txt")
        lines = [
            f"AI_OS 讨论日志",
            f"时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            f"议题: {self._topic if hasattr(self, '_topic') else ''}",
            f"总轮数: {result['总轮数']}",
            f"共识: {'达成' if result['共识达成'] else '未达成'}",
            "",
            "=== Agent状态 ===",
        ]
        for agent, state in result["Agent状态"].items():
            lines.append(f"{agent}: 发言{state['发言']}次, 跳过{state['跳过']}次, {'满意' if state['满意'] else '待定'}")
        
        lines.append("")
        lines.append("=== 观点摘要 ===")
        for view in result["观点汇总"]:
            lines.append(f"[{view['agent']}] {view['content']}")
        
        text_log.write_text("\n".join(lines))
        print(f"\n📄 日志已保存: {text_log}")
    
    async def _ceo_summary(self, topic: str):
        """CEO最终总结"""
        print("\n--- CEO总结 ---")
        
        # 构建总结prompt
        prompt = f"[CEO总结] 议题: {topic}\n\n"
        prompt += "各方观点摘要:\n"
        
        for i, round_outputs in enumerate(self.history[-3:]):  # 最近3轮
            for agent, resp in round_outputs.items():
                if resp and hasattr(resp, 'content') and resp.content:
                    prompt += f"- {agent}: {resp.content[:100]}...\n"
        
        prompt += "\n请作为CEO，综合各方观点，给出最终结论和行动建议（不超过200字）。直接输出文字即可。"
        
        # 调用CEO
        try:
            response = await self._call_llm("CEO", prompt)
            content = response.content if hasattr(response, 'content') else str(response)
            
            if not content or content.strip() == "":
                content = "各方已充分讨论，建议综合CFO财务分析与CTO技术方案，逐步推进。"
            
            if hasattr(self, 'on_event') and callable(self.on_event):
                self.on_event({"type": "ceo_summary", "content": content})
            
            print(f"CEO总结: {content[:100]}...")
        except Exception as e:
            print(f"CEO总结出错: {e}")
            # 发送默认总结
            if hasattr(self, 'on_event') and callable(self.on_event):
                self.on_event({"type": "ceo_summary", "content": "讨论已结束，请综合各方意见做出决策。"})
    
    def _determine_speakers(self) -> List[str]:
        """决定本轮发言者"""
        return [
            agent for agent in self.DEFAULT_ORDER
            if self.agent_state[agent]["active"] 
            and not self.agent_state[agent]["satisfied"]
            and self.llm_configs[agent]
        ]
    
    async def _run_round(self, speakers: List[str], topic: str, round_num: int) -> Dict:
        """执行一轮讨论"""
        round_outputs = {}
        queue = speakers.copy()
        
        while queue:
            speaker = queue.pop(0)
            prompt = self._build_prompt(speaker, topic, round_num)
            
            # 监控回调：Agent开始发言
            if hasattr(self, 'on_event') and callable(self.on_event):
                self.on_event({"type": "agent_start", "agent": speaker, "round": round_num})
            
            # 直接调用LLM API
            raw_response = await self._call_llm(speaker, prompt)
            
            response = self._parse_response(raw_response)
            
            if self._should_skip(response.content):
                print(f"  [{speaker}] 跳过本轮")
                response.skipped = True
                self.agent_state[speaker]["skip_count"] += 1
                round_outputs[speaker] = response
                # 监控回调：Agent跳过
                if hasattr(self, 'on_event') and callable(self.on_event):
                    self.on_event({"type": "agent_done", "agent": speaker, "skipped": True})
                continue
            
            self.agent_state[speaker]["speak_count"] += 1
            if response.satisfied:
                self.agent_state[speaker]["satisfied"] = True
                print(f"  [{speaker}] ✓ 满意")
            
            # 处理指定下一位发言者 - 追加而非替换
            if response.next_speakers:
                new_speakers = [s for s in response.next_speakers 
                               if s in self.DEFAULT_ORDER 
                               and self.llm_configs.get(s)
                               and s not in queue  # 避免重复
                               and not self.agent_state[s]["satisfied"]]  # 跳过已满意的
                queue.extend(new_speakers)
                if new_speakers:
                    print(f"  [{speaker}] 指定下一位发言: {new_speakers}")
            
            summary = response.content[:80] + "..." if len(response.content) > 80 else response.content
            print(f"  [{speaker}] {summary}")
            
            # 监控回调：Agent发言完成
            if hasattr(self, 'on_event') and callable(self.on_event):
                self.on_event({
                    "type": "agent_done",
                    "agent": speaker,
                    "content": response.content,  # 完整内容
                    "satisfied": response.satisfied,
                    "next_speakers": response.next_speakers,
                    "concerns": response.concerns
                })
            
            round_outputs[speaker] = response
        
        return round_outputs
    
    async def _call_llm(self, agent: str, prompt: str) -> str:
        """直接调用腾讯GLM API"""
        cfg = self.llm_configs.get(agent)
        if not cfg:
            return "配置缺失"
        
        url = cfg['base_url'].rstrip('/') + '/chat/completions'
        
        headers = {
            "Authorization": f"Bearer {cfg['api_key']}",
            "Content-Type": "application/json"
        }
        
        # 简化prompt避免过长
        if len(prompt) > 1500:
            prompt = prompt[:1500] + "\n请简要发言。"
        
        payload = {
            "model": cfg['model'],
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": 1500,  # 增加输出长度，中文约700字
            "temperature": 0.7
        }
        
        try:
            print(f"  [{agent}] 调用中...")
            async with httpx.AsyncClient(timeout=45.0) as client:
                resp = await client.post(url, headers=headers, json=payload)
                resp.raise_for_status()
                data = resp.json()
                content = data.get('choices', [{}])[0].get('message', {}).get('content', '')
                print(f"  [{agent}] 完成")
                return content
        except httpx.TimeoutException:
            print(f"  [{agent}] 超时，跳过")
            return "跳过"
        except Exception as e:
            print(f"  [{agent}] API失败: {e}")
            return ""
    
    def _parse_response(self, raw: str) -> AgentResponse:
        """解析Agent响应"""
        if not raw:
            return AgentResponse(content="")
        
        # 尝试JSON解析
        try:
            if "```json" in raw:
                start = raw.find("```json") + 7
                end = raw.find("```", start)
                json_str = raw[start:end].strip()
            elif "{" in raw and "}" in raw:
                start = raw.find("{")
                end = raw.rfind("}") + 1
                json_str = raw[start:end]
            else:
                return AgentResponse(content=raw)
            
            parsed = json.loads(json_str)
            return AgentResponse(
                content=parsed.get("content", raw),
                satisfied=parsed.get("satisfied", False),
                next_speakers=parsed.get("next_speakers", []),
                concerns=parsed.get("concerns", [])
            )
        except:
            return AgentResponse(content=raw)
    
    def _should_skip(self, content: str) -> bool:
        """判断是否跳过"""
        if not content:
            return True
        content = content.strip()
        # 只有明确单独说"跳过"才跳过，不匹配JSON内部的
        # 放宽条件：至少要有实质内容
        if len(content) < 5:
            return True
        # 明确的跳过声明（单独一行或短回复）
        lines = content.strip().split('\n')
        if len(lines) == 1 and len(lines[0]) < 20 and ("跳过" in lines[0] or lines[0].lower() == "pass"):
            return True
        return False
    
    def _build_prompt(self, speaker: str, topic: str, round_num: int) -> str:
        """构建讨论prompt"""
        roles = {
            "CEO": "CEO，负责战略决策和整体方向把控",
            "CFO": "CFO，关注财务可行性、成本收益分析",
            "CTO": "CTO，关注技术可行性、实现路径、风险",
            "CMO": "CMO，关注市场接受度、用户价值、推广策略"
        }
        
        prompt = f"[Round {round_num}] 你是{roles[speaker]}\n议题: {topic}\n\n"
        
        # 历史摘要
        recent = self.history[-self.config.context_window:] if self.history else []
        if recent:
            prompt += "[近期讨论]\n"
            for r_outputs in recent:
                for agent, resp in r_outputs.items():
                    if resp.content and not resp.skipped:
                        short = resp.content[:120] + "..." if len(resp.content) > 120 else resp.content
                        prompt += f"  {agent}: {short}\n"
        
        # 判断是否所有Agent都已发言
        all_spoken = all(
            self.agent_state[a]["speak_count"] > 0 
            for a in self.DEFAULT_ORDER 
            if self.llm_configs.get(a)
        )
        
        prompt += f"""
请发表观点，JSON格式返回:
{{"content":"观点","satisfied":false,"next_speakers":[],"concerns":[]}}

- content: 你的观点（简明扼要，100字以内）
- satisfied: 是否满意当前讨论结果
  - 设为true的条件：你的核心观点已表达，其他Agent的担忧已得到回应，且讨论已充分
  - 设为false：还需要更多信息或其他Agent补充
- next_speakers: 指定下一位发言者如["CTO"]，空数组表示按默认顺序
- concerns: 你的担忧点

注意：
1. 作为{speaker}，必须从你的角色视角发言
2. 如果还没发言过，不要跳过
{"3. 所有Agent都已发言过，如认为讨论充分可设satisfied:true" if all_spoken else ""}
"""
        return prompt
    
    def _check_consensus(self) -> bool:
        """检查共识 - 多维度判断"""
        # 方式1: 满意人数
        satisfied_count = sum(1 for s in self.agent_state.values() if s["satisfied"])
        if satisfied_count >= 3:
            return True
        
        # 方式2: 所有Agent都至少发言过1次 + 最近一轮无人有concerns
        all_spoken = all(s["speak_count"] > 0 for s in self.agent_state.values())
        if not all_spoken:
            return False
        
        # 检查最近一轮发言中是否包含共识信号
        if not self.history:
            return False
        
        last_round = self.history[-1]
        consensus_signals = ["同意", "赞同", "认可", "一致", "共识"]
        agree_count = 0
        total_content = ""
        
        for agent, resp in last_round.items():
            if resp.content and not resp.skipped:
                total_content += resp.content
                if any(sig in resp.content for sig in consensus_signals):
                    agree_count += 1
        
        # 超过半数Agent表达同意
        if agree_count >= 3:
            return True
        
        return False
    
    def _summarize(self) -> Dict:
        """生成摘要"""
        states = {
            agent: {
                "发言": s["speak_count"],
                "跳过": s["skip_count"],
                "满意": s["satisfied"]
            }
            for agent, s in self.agent_state.items()
        }
        
        views = []
        for r in self.history:
            for agent, resp in r.items():
                if resp.content and not resp.skipped:
                    views.append({"agent": agent, "content": resp.content[:150]})
        
        return {
            "总轮数": len(self.history),
            "Agent状态": states,
            "共识达成": self._check_consensus(),
            "观点汇总": views
        }


async def test_discussion():
    """测试"""
    engine = DiscussionEngine()
    result = await engine.run("是否应该先做demo验证方案可行性")
    print("\n" + "="*50)
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    asyncio.run(test_discussion())