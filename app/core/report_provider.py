"""
ReportProvider — 报告提供者接口

定义所有模块提供报告能力的抽象接口。
报告管理模块通过此接口聚合各模块的报告数据。

设计原则:
- 数据归属: 报告数据由产生数据的模块管理（不创建冗余表）
- 接口抽象: 通过 ReportProvider 接口让模块暴露报告能力
- 优雅降级: 模块未加载时，其报告类型不显示

使用示例:
    # 在 vision 模块中实现
    class VisionReportProvider(ReportProvider):
        def get_report_type(self) -> str:
            return 'vision'
        
        def get_user_reports(self, user_id) -> List[ReportInfo]:
            records = TestRecord.query.filter_by(user_id=user_id).all()
            return [ReportInfo(...) for r in records]
    
    # 在模块注册时
    def on_app_ready(self, app):
        from app.core.report_registry import ReportRegistry
        ReportRegistry.register(VisionReportProvider())
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Dict, Optional


@dataclass
class ReportInfo:
    """
    报告信息数据类（用于列表展示）
    
    Attributes:
        report_id: 报告唯一标识（如 session_id）
        report_type: 报告类型标识（如 'vision'）
        title: 报告标题
        created_at: 创建时间
        is_completed: 是否完成
        meta: 元数据（灵活扩展，如 {'eye': 'L', 'test_mode': 'Standard'}）
    """
    report_id: str
    report_type: str
    title: str
    created_at: datetime
    is_completed: bool = False
    meta: Dict = field(default_factory=dict)
    
    @property
    def date_group(self) -> str:
        """
        自动计算日期分组
        
        Returns:
            'today' | 'this_week' | 'this_month' | 'older'
        """
        now = datetime.utcnow()
        delta = now - self.created_at
        
        if delta.days == 0:
            return 'today'
        elif delta.days <= 7:
            return 'this_week'
        elif delta.days <= 30:
            return 'this_month'
        else:
            return 'older'


class ReportProvider(ABC):
    """
    报告提供者抽象基类
    
    所有需要提供报告能力的模块必须实现此接口。
    报告管理模块通过 ReportRegistry 调用各提供者的方法。
    """
    
    @abstractmethod
    def get_report_type(self) -> str:
        """
        返回报告类型标识
        
        用于筛选和路由匹配，如 'vision', 'acuity', 'color'
        
        Returns:
            报告类型字符串
        """
    
    @abstractmethod
    def get_display_name(self) -> str:
        """
        返回报告类型显示名称
        
        用于 UI 展示，如 '视野检查', '视力测试'
        
        Returns:
            显示名称字符串
        """
    
    @abstractmethod
    def get_user_reports(self, user_id: int, filters: Optional[Dict] = None) -> List[ReportInfo]:
        """
        获取用户的报告列表
        
        Args:
            user_id: 用户 ID
            filters: 可选筛选条件，如 {'eye': 'L', 'completed': True}
        
        Returns:
            ReportInfo 列表
        """
    
    @abstractmethod
    def get_report_route(self, report_id: str) -> str:
        """
        返回报告详情页路由
        
        Args:
            report_id: 报告唯一标识
        
        Returns:
            路由路径，如 '/analysis/report/<id>'
        """
    
    @abstractmethod
    def delete_report(self, report_id: str, user_id: int) -> bool:
        """
        删除报告
        
        Args:
            report_id: 报告唯一标识
            user_id: 用户 ID（用于权限验证）
        
        Returns:
            是否删除成功
        """
    
    def get_report_count(self, user_id: int) -> int:
        """
        获取用户报告数量（可选实现）
        
        Args:
            user_id: 用户 ID
        
        Returns:
            报告数量
        """
        return len(self.get_user_reports(user_id))
    
    def get_report_detail(self, report_id: str, user_id: int) -> Optional[Dict]:
        """
        获取报告详情（可选实现）
        
        用于 API 返回详细数据，不实现则返回 None
        
        Args:
            report_id: 报告唯一标识
            user_id: 用户 ID
        
        Returns:
            报告详情字典或 None
        """
        return None