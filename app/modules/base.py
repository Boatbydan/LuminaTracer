"""
BaseModule — 功能模块抽象基类

定义所有功能模块必须实现的接口契约。
系统启动时通过 discover_and_load() 自动发现并实例化各模块。

设计原则:
- 约定优于配置：放入 modules/ 目录即自动发现
- 优雅降级：模块加载失败不影响其他模块和系统启动
- 接口隔离：每个模块只通过 register() 与核心框架交互

使用示例:
    # 在 modules/my_feature/__init__.py 中
    from ..base import BaseModule, ModuleInfo
    
    class MyFeatureModule(BaseModule):
        @property
        def info(self) -> ModuleInfo:
            return ModuleInfo(
                module_id="my_feature",
                name="我的功能",
                name_en="My Feature",
                icon="bi-star",
                description="功能描述",
                version="1.0.0"
            )
        
        def register(self, app):
            from .routes import bp
            app.register_blueprint(bp)
    
    def create_module():
        return MyFeatureModule()
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Optional, Dict, Any, List
from flask import Flask


@dataclass(frozen=True)
class ModuleInfo:
    """
    模块元信息（不可变数据类）
    
    用于 Hub 展示、API 返回、模块间查询。
    frozen=True 保证注册后不可被意外修改。
    
    Attributes:
        module_id: 唯一标识符，如 "vision", "acuity", "color"
        name: 中文显示名称
        name_en: 英文显示名称（预留国际化）
        icon: Bootstrap Icons 类名，如 "bi-eye-fill", "bi-star"
        description: 模块描述文本
        version: 语义化版本号，如 "1.0.0"
        category: 分类标识，用于 Hub 分组展示
        badge: 可选标签，如 "核心", "Beta", "实验"
        route_endpoint: Flask 路由端点，模块入口页
        sort_order: 排序权重，数值越小越靠前
        meta: 扩展元数据，存放任意额外信息
        enabled: 是否启用（可用于功能开关）
    """
    module_id: str
    name: str
    name_en: str
    icon: str
    description: str
    version: str = "0.1.0"
    category: str = "default"
    badge: Optional[str] = None
    route_endpoint: str = ""
    sort_order: int = 100
    meta: Dict[str, Any] = field(default_factory=dict)
    enabled: bool = True


class BaseModule(ABC):
    """
    功能模块抽象基类 (ABC)
    
    所有功能模块必须继承此类并实现抽象方法。
    系统在启动时自动扫描 modules/ 子目录，
    调用各模块的 create_module() 工厂函数获取实例。
    
    生命周期:
        1. discover_and_load() 扫描目录
        2. 调用 create_module() 创建实例
        3. 调用 register(app) 注册蓝图/模型/CLI
        4. 所有模块注册完后调用 on_app_ready(app)
        5. 运行时可通过 health_check() 检查状态
    """

    @property
    @abstractmethod
    def info(self) -> ModuleInfo:
        """返回模块元信息"""

    @abstractmethod
    def register(self, app: Flask) -> None:
        """
        注册模块到 Flask 应用
        
        在此方法中完成:
        - app.register_blueprint() 注册路由蓝图
        - 数据库模型初始化（如有新表）
        - CLI 命令注册
        - 其他模块级初始化
        
        注意: 此方法中的异常会被 discover_and_load() 捕获，
              不会导致整个应用崩溃（优雅降级）。
        
        Args:
            app: Flask 应用实例
        """

    def on_app_ready(self, app: Flask) -> None:
        """
        可选钩子 — 所有模块注册完毕后回调
        
        使用场景:
        - 跨模块依赖解析（如 vision 模块需要 api 模块的某个服务）
        - 全局事件监听注册
        - 后台任务启动
        - 缓存预热
        
        默认实现为空操作。覆写此方法时请自行处理异常。
        
        Args:
            app: Flask 应用实例（已完全初始化）
        """
        pass

    def health_check(self) -> Dict[str, Any]:
        """
        可选 — 健康检查
        
        Returns:
            包含 status 和详细信息的字典
            
        Example::
            {'status': 'ok', 'module': 'vision', 'details': {'db': 'connected'}}
        """
        return {
            'status': 'ok',
            'module': self.info.module_id,
            'version': self.info.version
        }
    
    def get_report_provider(self) -> Optional['ReportProvider']:
        """
        可选 — 返回报告提供者
        
        如果模块需要提供报告管理能力，实现此方法返回 ReportProvider 实例。
        报告管理模块会自动聚合各模块的报告数据。
        
        Returns:
            ReportProvider 实例或 None（默认不提供报告能力）
        
        Example::
            from app.core.report_provider import ReportProvider
            from .report_provider import VisionReportProvider
            
            def get_report_provider(self) -> ReportProvider:
                return VisionReportProvider()
        """
        return None