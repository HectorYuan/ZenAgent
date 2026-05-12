"""
技术趋势分析器 (Tech Trend Analyzer)

专门分析技术领域趋势:
- 技术关键词提取
- 技术栈趋势
- 新兴技术识别
"""

from typing import Dict, List, Any, Optional, Set
from dataclasses import dataclass, field
from datetime import datetime
import re
import logging

from .trend_analyzer import TrendAnalyzer, Trend, TrendType, TrendSource

logger = logging.getLogger(__name__)


@dataclass
class TechKeyword:
    """技术关键词"""
    keyword: str
    category: str  # language, framework, tool, concept
    frequency: int = 0
    related_keywords: Set[str] = field(default_factory=set)
    first_seen: datetime = field(default_factory=datetime.now)
    last_seen: datetime = field(default_factory=datetime.now)


class TechKeywordExtractor:
    """技术关键词提取器"""
    
    # 预定义技术类别
    TECH_CATEGORIES = {
        'language': {
            'python', 'javascript', 'java', 'typescript', 'go', 'rust', 
            'c++', 'c#', 'ruby', 'swift', 'kotlin', 'scala', 'php'
        },
        'framework': {
            'react', 'vue', 'angular', 'django', 'flask', 'spring',
            'express', 'fastapi', 'next.js', 'nuxt', 'rails', 'laravel'
        },
        'ai_ml': {
            'tensorflow', 'pytorch', 'keras', 'scikit-learn', 'transformers',
            'llm', 'gpt', 'bert', 'neural', 'machine learning', 'deep learning'
        },
        'cloud': {
            'aws', 'azure', 'gcp', 'kubernetes', 'docker', 'serverless',
            'lambda', 'cloudformation', 'terraform'
        },
        'database': {
            'postgresql', 'mysql', 'mongodb', 'redis', 'elasticsearch',
            'cassandra', 'dynamodb', 'sql', 'nosql'
        },
        'devops': {
            'ci/cd', 'jenkins', 'gitlab', 'github actions', 'ansible',
            'monitoring', 'logging', 'prometheus', 'grafana'
        }
    }
    
    # 新兴技术关键词
    EMERGING_TECH = {
        'generative ai', 'chatgpt', 'llm', 'rag', 'agent',
        'web3', 'metaverse', 'edge computing', 'quantum',
        'serverless', 'wasm', 'webassembly', 'copilot'
    }
    
    def __init__(self):
        self.known_keywords: Dict[str, TechKeyword] = {}
        self._build_keyword_index()
    
    def _build_keyword_index(self):
        """构建关键词索引"""
        for category, keywords in self.TECH_CATEGORIES.items():
            for keyword in keywords:
                self.known_keywords[keyword.lower()] = TechKeyword(
                    keyword=keyword,
                    category=category
                )
    
    def extract_from_text(self, text: str) -> List[TechKeyword]:
        """从文本中提取技术关键词"""
        text_lower = text.lower()
        found = []
        
        # 匹配已知关键词
        for keyword_lower, tech_keyword in self.known_keywords.items():
            if keyword_lower in text_lower:
                tech_keyword.frequency += 1
                tech_keyword.last_seen = datetime.now()
                found.append(tech_keyword)
        
        # 检测新兴技术
        for tech in self.EMERGING_TECH:
            if tech in text_lower:
                if tech not in self.known_keywords:
                    self.known_keywords[tech] = TechKeyword(
                        keyword=tech,
                        category='emerging'
                    )
                self.known_keywords[tech].frequency += 1
                found.append(self.known_keywords[tech])
        
        return found
    
    def get_trending_keywords(
        self,
        min_frequency: int = 5,
        limit: int = 20
    ) -> List[TechKeyword]:
        """获取热门关键词"""
        trending = [
            k for k in self.known_keywords.values()
            if k.frequency >= min_frequency
        ]
        trending.sort(key=lambda k: k.frequency, reverse=True)
        return trending[:limit]


class TechTrendAnalyzer:
    """
    技术趋势分析器
    
    分析技术领域的趋势:
    - 技术栈变化
    - 新兴技术
    - 技术热点
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        
        self.keyword_extractor = TechKeywordExtractor()
        
        # 趋势窗口
        self.window_size = self.config.get('window_size', 7)  # 天
        self.min_keyword_frequency = self.config.get('min_frequency', 3)
        
        # 技术趋势历史
        self.tech_trends: Dict[str, Trend] = {}
    
    def analyze(self, data: List[Dict[str, Any]]) -> List[Trend]:
        """
        分析技术趋势
        
        Args:
            data: 输入数据，每项包含text字段
            
        Returns:
            List[Trend]: 识别到的技术趋势
        """
        trends = []
        
        # 合并所有文本
        all_text = ' '.join(
            item.get('text', '') for item in data
        )
        
        # 提取关键词
        keywords = self.keyword_extractor.extract_from_text(all_text)
        
        # 按类别聚合
        by_category: Dict[str, List[TechKeyword]] = {}
        for kw in keywords:
            if kw.keyword not in by_category:
                by_category[kw.keyword] = []
            by_category[kw.keyword].append(kw)
        
        # 生成趋势
        for keyword, kws in by_category.items():
            if len(kws) < self.min_keyword_frequency:
                continue
            
            category = kws[0].category
            trend_type = self._determine_trend_type(kws[0], category)
            
            trend = Trend(
                trend_id=self._generate_trend_id(keyword),
                name=f"Tech: {keyword}",
                description=f"Technology trend for {keyword}",
                trend_type=trend_type,
                source=TrendSource.TECHNICAL,
                score=self._calculate_score(kws),
                confidence=self._calculate_confidence(kws),
                volume=len(kws),
                keywords=[keyword, category],
                velocity=self._calculate_velocity(kws)
            )
            
            trends.append(trend)
            self.tech_trends[trend.trend_id] = trend
        
        return trends
    
    def _determine_trend_type(self, keyword: TechKeyword, category: str) -> TrendType:
        """判断趋势类型"""
        # 新兴技术
        if category == 'emerging':
            return TrendType.EMERGING
        
        # 检查是否是热门新兴技术
        if keyword.keyword.lower() in TechKeywordExtractor.EMERGING_TECH:
            return TrendType.EMERGING
        
        # 基于频率变化趋势
        # 简化处理：频率高为上升趋势
        if keyword.frequency > 20:
            return TrendType.RISING
        elif keyword.frequency > 10:
            return TrendType.STABLE
        else:
            return TrendType.DECLINING
    
    def _calculate_score(self, keywords: List[TechKeyword]) -> float:
        """计算趋势得分"""
        frequency = len(keywords)
        recency_factor = self._calculate_recency_factor(keywords)
        
        # 基础分数来自频率
        base_score = min(100, frequency * 5)
        
        # 新兴技术加分
        category_bonus = 10 if keywords[0].category == 'emerging' else 0
        
        return base_score * recency_factor + category_bonus
    
    def _calculate_confidence(self, keywords: List[TechKeyword]) -> float:
        """计算置信度"""
        if len(keywords) >= 10:
            return 0.9
        elif len(keywords) >= 5:
            return 0.7
        elif len(keywords) >= 3:
            return 0.5
        return 0.3
    
    def _calculate_velocity(self, keywords: List[TechKeyword]) -> float:
        """计算变化速度"""
        if len(keywords) < 2:
            return 0.0
        
        # 简化: 使用时间跨度作为速度代理
        time_span = (keywords[-1].last_seen - keywords[0].first_seen).days
        if time_span == 0:
            time_span = 1
        
        return len(keywords) / time_span
    
    def _calculate_recency_factor(self, keywords: List[TechKeyword]) -> float:
        """计算时效性因子"""
        now = datetime.now()
        last_seen = keywords[-1].last_seen if keywords else now
        days_ago = (now - last_seen).days
        
        if days_ago <= 1:
            return 1.0
        elif days_ago <= 7:
            return 0.8
        elif days_ago <= 30:
            return 0.5
        else:
            return 0.2
    
    def _generate_trend_id(self, keyword: str) -> str:
        """生成趋势ID"""
        import hashlib
        content = f"tech:{keyword}:{datetime.now().date()}"
        return hashlib.md5(content.encode()).hexdigest()[:12]
    
    def get_category_distribution(self) -> Dict[str, int]:
        """获取技术类别分布"""
        distribution = {}
        for keyword in self.keyword_extractor.known_keywords.values():
            cat = keyword.category
            distribution[cat] = distribution.get(cat, 0) + keyword.frequency
        return distribution
    
    def get_emerging_tech_report(self) -> List[Dict[str, Any]]:
        """获取新兴技术报告"""
        emerging = [
            k for k in self.keyword_extractor.known_keywords.values()
            if k.category == 'emerging' and k.frequency > 0
        ]
        
        emerging.sort(key=lambda k: k.frequency, reverse=True)
        
        return [
            {
                'keyword': k.keyword,
                'frequency': k.frequency,
                'first_seen': k.first_seen.isoformat(),
                'last_seen': k.last_seen.isoformat()
            }
            for k in emerging
        ]
