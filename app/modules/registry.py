"""
Module Runtime Registry — 运行时模块注册表

提供两层注册能力:
1. ModuleRuntimeRegistry — 新体系：管理 BaseModule 实例（用于 discover_and_load）
2. TestModuleRegistry — 旧体系：管理 TestModule 数据类（向后兼容）

迁移期间两者共存。最终目标: 全部迁移到 BaseModule 体系后移除 TestModule。

查询接口（统一）:
    ModuleRuntimeRegistry.get_all()      → 所有已加载的 BaseModule
    ModuleRuntimeRegistry.get_enabled()   → 所有 enabled=True 的模块
    ModuleRuntimeRegistry.get(id)         → 按 module_id 查找

Hub 页面使用示例:
    from app.modules import ModuleRuntimeRegistry
    
    modules = ModuleRuntimeRegistry.get_enabled()
    for m in modules:
        print(m.info.name, m.info.icon, m.info.route_endpoint)
"""

from typing import Optional, List, Dict, Any
from dataclasses import dataclass, field
from .base import BaseModule


class ModuleRuntimeRegistry:
    """
    BaseModule 运行时注册表（新体系）
    
    由 discover_and_load() 自动填充。
    提供线程安全的查询接口。
    
    设计原则:
    - 写入时机: 应用启动时 (discover_and_load)
    - 读取向: 请求处理时 (模板渲染、API 返回)
    - 生命周期: 与应用进程一致
    """
    
    _instances: Dict[str, BaseModule] = {}

    @classmethod
    def register(cls, module: BaseModule) -> None:
        """
        注册一个已初始化的模块实例
        
        Args:
            module: BaseModule 实例
            
        Raises:
            ValueError: 如果 module_id 已存在
        """
        mid = module.info.module_id
        if mid in cls._instances:
            raise ValueError(
                f"Module '{mid}' already registered. "
                f"Duplicate module_id detected."
            )
        cls._instances[mid] = module

    @classmethod
    def unregister(cls, module_id: str) -> bool:
        """注销模块"""
        return cls._instances.pop(module_id, None) is not None

    @classmethod
    def get(cls, module_id: str) -> Optional[BaseModule]:
        """按 ID 获取模块实例"""
        return cls._instances.get(module_id)

    @classmethod
    def get_all(cls) -> List[BaseModule]:
        """获取所有已注册模块"""
        return list(cls._instances.values())

    @classmethod
    def get_enabled(cls) -> List[BaseModule]:
        """获取所有已启用的模块，按 sort_order 排序"""
        enabled = [m for m in cls._instances.values() if m.info.enabled]
        return sorted(enabled, key=lambda m: m.info.sort_order)

    @classmethod
    def get_by_category(cls, category: str) -> List[BaseModule]:
        """获取指定分类的已启用模块"""
        return [
            m for m in cls._instances.values()
            if m.info.category == category and m.info.enabled
        ]

    @classmethod
    def count(cls) -> int:
        """已注册模块总数"""
        return len(cls._instances)

    @classmethod
    def count_enabled(cls) -> int:
        """已启用模块数量"""
        return sum(1 for m in cls._instances.values() if m.info.enabled)

    @classmethod
    def get_info_list(cls) -> List[Dict[str, Any]]:
        """
        获取所有已启用模块的 info 字典列表
        
        用于 Hub 展示和 JSON API 返回，
        避免模板直接访问 BaseModule 实例。
        
        Returns:
            ModuleInfo 数据字典列表
        """
        result = []
        for m in cls.get_enabled():
            info = m.info
            result.append({
                'module_id': info.module_id,
                'name': info.name,
                'name_en': info.name_en,
                'icon': info.icon,
                'description': info.description,
                'version': info.version,
                'category': info.category,
                'badge': info.badge,
                'route_endpoint': info.route_endpoint,
                'sort_order': info.sort_order,
                'meta': info.meta,
            })
        return result

    @classmethod
    def clear(cls) -> None:
        """清空所有注册（主要用于测试）"""
        cls._instances.clear()


# ============================================================
# 向后兼容层：旧的 TestModule 注册表
# ============================================================

@dataclass(frozen=True)
class TestModule:
    """
    旧版测试模块定义（保留向后兼容）
    
    .. deprecated::
        新代码请使用 BaseModule + ModuleInfo。
        此类将在所有模块迁移完成后移除。
    """
    module_id: str
    name: str
    name_en: str
    icon: str
    description: str
    route_endpoint: str
    enabled: bool = True
    badge: Optional[str] = None
    category: str = "default"
    meta: Dict[str, Any] = field(default_factory=dict)
    sort_order: int = 100

    @property
    def display_name(self) -> str:
        return self.name

    @property
    def url(self) -> str:
        from flask import url_for
        return url_for(self.route_endpoint)


class TestModuleRegistry:
    """
    旧版测试模块注册表（向后兼容）
    
    .. deprecated::
        请使用 ModuleRuntimeRegistry。
        此类仅在迁移过渡期保留。
    """
    _modules: Dict[str, TestModule] = {}
    _categories: Dict[str, str] = {
        "default": "默认",
        "visual": "视觉功能",
        "acuity": "视力检查",
        "color": "色觉测试",
        "contrast": "对比敏感度",
    }

    @classmethod
    def register(cls, module: TestModule) -> None:
        if module.module_id in cls._modules:
            raise ValueError(
                f"Module '{module.module_id}' already registered."
            )
        cls._modules[module.module_id] = module

    @classmethod
    def unregister(cls, module_id: str) -> bool:
        return cls._modules.pop(module_id, None) is not None

    @classmethod
    def get(cls, module_id: str) -> Optional[TestModule]:
        return cls._modules.get(module_id)

    @classmethod
    def get_all_enabled(cls) -> List[TestModule]:
        enabled = [m for m in cls._modules.values() if m.enabled]
        return sorted(enabled, key=lambda m: m.sort_order)

    @classmethod
    def get_by_category(cls, category: str) -> List[TestModule]:
        return [
            m for m in cls._modules.values()
            if m.category == category and m.enabled
        ]

    @classmethod
    def get_categories(cls) -> List[Dict[str, Any]]:
        result = []
        for cat_id, cat_name in cls._categories.items():
            modules = cls.get_by_category(cat_id)
            if modules:
                result.append({
                    'id': cat_id,
                    'name': cat_name,
                    'modules': modules,
                    'count': len(modules)
                })
        return result

    @classmethod
    def register_category(cls, category_id: str, display_name: str) -> None:
        cls._categories[category_id] = display_name

    @classmethod
    def count(cls) -> int:
        return len(cls._modules)

    @classmethod
    def count_enabled(cls) -> int:
        return sum(1 for m in cls._modules.values() if m.enabled)

    @classmethod
    def clear(cls) -> None:
        cls._modules.clear()


def register_builtin_modules():
    """
    注册内置测试模块（兼容层）
    
    在迁移完成前，此函数同时向新旧两个注册表写入。
    迁移完成后可删除此函数。
    """