"""
Modules Package — 功能模块发现与加载系统

提供自动发现、加载、管理功能模块的能力。

架构:
    app/modules/
    ├── __init__.py      ← 本文件：发现器 + 加载器
    ├── base.py          ← BaseModule ABC + ModuleInfo
    ├── registry.py      ← 运行时注册表（向后兼容 TestModule）
    ├── vision/          ← 视野测试模块
    │   └── __init__.py  # def create_module() -> VisionModule
    └── _template/       ← 新模块脚手架

使用方式:
    # 在 app/__init__.py 的 create_app() 中:
    from .modules import discover_and_load
    loaded_modules = discover_and_load(app)

约定:
    - 每个模块是一个子目录，目录名即 module_id
    - 目录名以 _ 开头的被视为特殊目录（如 _template），跳过
    - 每个模块必须导出 create_module() 工厂函数
    - 模块加载失败不影响其他模块（优雅降级）
"""

import importlib
import sys
import traceback
from pathlib import Path
from typing import List, Dict, Any, Optional
from flask import Flask

from .base import BaseModule
from .registry import ModuleRuntimeRegistry

# ──────────────────────────────────────────────
#  模块清单 — 显式声明所有可用模块
# ──────────────────────────────────────────────
# 新增模块时在此列表添加 module_id 即可。
# 此清单确保 PyInstaller 打包后仍能正确发现模块
# （frozen 环境下文件系统目录结构不可用）。
MODULE_MANIFEST = [
    "vision",
    "chromagrid",
    "reports",
]


def _discover_from_filesystem() -> List[str]:
    """
    从文件系统扫描模块目录（开发模式后备方案）

    仅在非 frozen 环境下使用，用于自动发现新增模块
    而无需手动更新 MODULE_MANIFEST。
    """
    modules_dir = Path(__file__).parent
    candidates = sorted(
        item.name for item in modules_dir.iterdir()
        if item.is_dir() and not item.name.startswith('_')
    )
    # 合并：文件系统发现的 + 清单中的，去重
    seen = set(MODULE_MANIFEST)
    for name in candidates:
        if name not in seen:
            seen.add(name)
    return sorted(seen)


def discover_and_load(app: Flask) -> List[BaseModule]:
    """
    发现并加载所有可用模块

    发现策略:
    - frozen 环境 (PyInstaller): 使用 MODULE_MANIFEST 显式清单
    - 开发环境: 优先使用清单，同时扫描文件系统补充新模块

    加载流程:
    1. 尝试导入 app.modules.{module_id}
    2. 调用 create_module() 获取 BaseModule 实例
    3. 调用 instance.register(app) 注册 Blueprint
    4. 成功的实例加入 ModuleRuntimeRegistry

    优雅降级:
        - 导入失败 → 打印警告，跳过该模块
        - create_module() 不存在 → 跳过
        - register() 抛异常 → 打印完整 trace，跳过
        - 以上情况均不阻止应用启动

    Args:
        app: 已完成核心扩展初始化的 Flask 应用实例

    Returns:
        成功加载的模块实例列表
    """
    if getattr(sys, 'frozen', False):
        # PyInstaller 环境: 仅使用显式清单
        module_ids = list(MODULE_MANIFEST)
    else:
        # 开发环境: 清单 + 文件系统扫描
        module_ids = _discover_from_filesystem()

    loaded: List[BaseModule] = []
    failed: List[Dict[str, str]] = []

    for module_id in module_ids:
        try:
            mod = importlib.import_module(f'app.modules.{module_id}')

            if not hasattr(mod, 'create_module'):
                print(f"[Module] ⚠ {module_id}: missing create_module(), skipped")
                failed.append({'id': module_id, 'reason': 'no factory'})
                continue

            factory = getattr(mod, 'create_module')
            instance = factory()

            if not isinstance(instance, BaseModule):
                print(f"[Module] ⚠ {module_id}: create_module() must return BaseModule instance")
                failed.append({'id': module_id, 'reason': 'invalid type'})
                continue

            instance.register(app)
            ModuleRuntimeRegistry.register(instance)
            loaded.append(instance)

            info = instance.info
            badge_str = f" [{info.badge}]" if info.badge else ""
            print(
                f"[Module] [OK] {info.name}{badge_str} "
                f"v{info.version} (id={info.module_id})"
            )

        except Exception as e:
            tb = traceback.format_exc()
            print(f"[Module] [FAIL] {module_id} load FAILED:\n{tb}")
            failed.append({'id': module_id, 'reason': str(e)})

    print(f"\n[Module] Summary: {len(loaded)} loaded, {len(failed)} skipped")
    if failed:
        for f in failed:
            print(f"         - {f['id']}: {f['reason']}")

    return loaded


def trigger_app_ready(app: Flask, modules: List[BaseModule]) -> None:
    """
    所有模块注册完毕后，触发 on_app_ready 钩子
    
    Args:
        app: Flask 应用实例
        modules: 已成功加载的模块列表
    """
    for module in modules:
        try:
            module.on_app_ready(app)
        except Exception as e:
            print(f"[Module] ! {module.info.module_id}.on_app_ready() error: {e}")


__all__ = [
    'BaseModule',
    'ModuleInfo',
    'discover_and_load',
    'trigger_app_ready',
    'ModuleRuntimeRegistry',
    'TestModule',
    'TestModuleRegistry',
]

from .base import BaseModule, ModuleInfo
from .registry import ModuleRuntimeRegistry, TestModule, TestModuleRegistry