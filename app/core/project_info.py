"""
Project Info — 项目身份信息的唯一数据源 (Single Source of Truth)

所有项目元信息（版本、链接、作者等）集中管理于此。
上层通过 context_processor 自动注入模板，或直接 import 使用。

修改规则:
  - 新增字段: 在此文件添加常量 + 更新 get_identity() 返回值
  - 修改版本/链接: 只改此文件，全局自动生效
"""

__all__ = [
    'VERSION', 'PROJECT_NAME', 'AUTHOR', 'DESCRIPTION',
    'GITHUB_URL', 'GITHUB_ISSUES_URL', 'GITHUB_RELEASES_URL',
    'TUTORIAL_URL', 'LICENSE',
    'get_identity',
]

VERSION = "1.1.0"
PROJECT_NAME = "Lumina Tracer"
AUTHOR = "Boatbydan"
DESCRIPTION = "Open Source Vision Checker"
LICENSE = "MIT"

GITHUB_URL = "https://github.com/Boatbydan/LuminaTracer"
GITHUB_ISSUES_URL = f"{GITHUB_URL}/issues"
GITHUB_RELEASES_URL = f"{GITHUB_URL}/releases"
TUTORIAL_URL = "https://www.bilibili.com/video/BV1bLoDBeEWr"


def get_identity() -> dict:
    """Return all project metadata as a dict, keyed for template injection."""
    return {
        'project_version': VERSION,
        'project_name': PROJECT_NAME,
        'project_author': AUTHOR,
        'project_description': DESCRIPTION,
        'project_license': LICENSE,
        'project_github': GITHUB_URL,
        'project_issues': GITHUB_ISSUES_URL,
        'project_releases': GITHUB_RELEASES_URL,
        'project_tutorial': TUTORIAL_URL,
    }
