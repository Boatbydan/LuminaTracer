"""
ReportRegistry — 报告提供者注册中心

管理所有模块的 ReportProvider 实例。
报告管理模块通过此注册中心聚合各模块的报告数据。

使用示例:
    # 注册提供者
    ReportRegistry.register(VisionReportProvider())
    
    # 获取所有报告
    reports = ReportRegistry.get_all_reports(user_id)
    
    # 按类型筛选
    vision_reports = ReportRegistry.get_reports_by_type('vision', user_id)
"""

from typing import Dict, List, Optional
from .report_provider import ReportProvider, ReportInfo


class ReportRegistry:
    """
    报告提供者注册中心
    
    在应用启动时由各模块注册其 ReportProvider。
    报告管理模块通过此注册中心查询和聚合报告。
    """
    
    _providers: Dict[str, ReportProvider] = {}
    
    @classmethod
    def register(cls, provider: ReportProvider) -> None:
        """
        注册报告提供者
        
        Args:
            provider: ReportProvider 实例
        
        Raises:
            ValueError: 如果报告类型已存在
        """
        report_type = provider.get_report_type()
        if report_type in cls._providers:
            raise ValueError(
                f"Report type '{report_type}' already registered."
            )
        cls._providers[report_type] = provider
        print(f"[ReportRegistry] Registered: {report_type} ({provider.get_display_name()})")
    
    @classmethod
    def unregister(cls, report_type: str) -> bool:
        """
        注销报告提供者
        
        Args:
            report_type: 报告类型标识
        
        Returns:
            是否成功注销
        """
        if report_type in cls._providers:
            del cls._providers[report_type]
            print(f"[ReportRegistry] Unregistered: {report_type}")
            return True
        return False
    
    @classmethod
    def get_provider(cls, report_type: str) -> Optional[ReportProvider]:
        """
        获取指定类型的报告提供者
        
        Args:
            report_type: 报告类型标识
        
        Returns:
            ReportProvider 实例或 None
        """
        return cls._providers.get(report_type)
    
    @classmethod
    def get_all_providers(cls) -> List[ReportProvider]:
        """
        获取所有已注册的报告提供者
        
        Returns:
            ReportProvider 列表
        """
        return list(cls._providers.values())
    
    @classmethod
    def get_all_reports(cls, user_id: int, filters: Optional[Dict] = None) -> List[ReportInfo]:
        """
        聚合所有模块的报告
        
        Args:
            user_id: 用户 ID
            filters: 可选筛选条件
        
        Returns:
            按时间排序的 ReportInfo 列表
        """
        all_reports = []
        for provider in cls._providers.values():
            try:
                reports = provider.get_user_reports(user_id, filters)
                all_reports.extend(reports)
            except Exception as e:
                print(f"[ReportRegistry] Error fetching reports from {provider.get_report_type()}: {e}")
        
        return sorted(all_reports, key=lambda r: r.created_at, reverse=True)
    
    @classmethod
    def get_reports_by_type(cls, report_type: str, user_id: int, filters: Optional[Dict] = None) -> List[ReportInfo]:
        """
        获取指定类型的报告
        
        Args:
            report_type: 报告类型标识
            user_id: 用户 ID
            filters: 可选筛选条件
        
        Returns:
            ReportInfo 列表
        """
        provider = cls.get_provider(report_type)
        if provider:
            return provider.get_user_reports(user_id, filters)
        return []
    
    @classmethod
    def get_type_list(cls) -> List[Dict]:
        """
        获取所有报告类型（用于筛选下拉框）
        
        Returns:
            [{'type': 'vision', 'name': '视野检查'}, ...]
        """
        return [
            {
                'type': p.get_report_type(),
                'name': p.get_display_name(),
                'count': p.get_report_count(0)  # 占位，实际调用时传入 user_id
            }
            for p in cls._providers.values()
        ]
    
    @classmethod
    def count(cls) -> int:
        """
        已注册的报告类型数量
        
        Returns:
            数量
        """
        return len(cls._providers)
    
    @classmethod
    def has_type(cls, report_type: str) -> bool:
        """
        检查报告类型是否已注册
        
        Args:
            report_type: 报告类型标识
        
        Returns:
            是否存在
        """
        return report_type in cls._providers
    
    @classmethod
    def clear(cls) -> None:
        """
        清空所有注册（主要用于测试）
        """
        cls._providers.clear()