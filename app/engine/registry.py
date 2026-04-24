# app/engine/registry.py

class StrategyRegistry:
    # 点位策略配置
    GRID_PATTERNS = {
        "24-2": {
            "display_name": "24-2 Grid",
            "description": "Standard 24-2 pattern with nasal step",
            "coords": [3, 9, 15, 21],
            "nasal_step": True
        },
        "10-2": {
            "display_name": "10-2 Grid",
            "description": "Central 10-2 pattern for macular testing",
            "coords": [3, 6, 9],
            "nasal_step": False
        }
    }
    
    # 测试模式配置
    TEST_MODES = {
        "standard": {
            "display_name": "Standard (标准模式)",
            "description": "Standard diagnostic sequence using Adaptive Bayesian Estimation",
            "core_algo": "ZEST",
            "params": {
                "min_stimulus": 0,
                "max_stimulus": 40,
                "dynamic_range": True
            }
        },
        "fast": {
            "display_name": "Fast (快速模式)",
            "description": "Optimized screening protocol with dynamic termination",
            "core_algo": "ZEST",
            "params": {
                "error_std": 1.5,
                "termination_criterion": "loose"
            }
        }
    }
    
    # 测试类别配置
    TEST_CATEGORIES = {
        "normal": {
            "display_name": "Normal Test (正常测试)",
            "description": "Full threshold mapping of all test points"
        },
        "incremental": {
            "display_name": "Reference Test (参考测试)",
            "description": "Tests only abnormal points based on previous test results",
            "params": {
                "threshold": 20,  # 敏感度阈值，低于此值的点被认为是异常
                "margin": 1.0     # 异常点周围的 margin 度数
            }
        }
    }

    MODES = {
        # 标准模式
        "mode_standard_v1": {
            "display_name": "Tracer Standard (标准模式)",
            "description": "Standard diagnostic sequence using Adaptive Bayesian Estimation. High precision for full threshold mapping.",
            "core_algo": "ZEST",  
            "grid_pattern": "24-2",
            "test_mode": "standard",
            "test_category": "normal",
            "params": {
                "domain": "24-2",
                "min_stimulus": 0,
                "max_stimulus": 40,
                "dynamic_range": True
            }
        },

        # 快速模式
        "mode_fast_v1": {
            # 改名：Tracer Rapid (快速筛查模式)
            "display_name": "Tracer Rapid (快速筛查模式)",
            "description": "Optimized screening protocol with dynamic termination. Prioritizes speed for population screening.",
            "core_algo": "ZEST", 
            "grid_pattern": "24-2",
            "test_mode": "fast",
            "test_category": "normal",
            "params": {
                "domain": "24-2", 
                "error_std": 1.5,
                "termination_criterion": "loose" 
            }
        },
        
        # 校准模式
        "mode_dev_test": {
            "display_name": "System Calibration (系统校准)",
            "description": "4-point fixed grid for hardware validation.",
            "core_algo": "FIXED_GRID",
            "grid_pattern": "custom",
            "test_mode": "standard",
            "test_category": "normal",
            "params": {
                "points_count": 4
            }
        }
    }

    @classmethod
    def get_all_modes(cls):
        return [
            {"id": k, "name": v["display_name"], "desc": v["description"]} 
            for k, v in cls.MODES.items()
        ]

    @classmethod
    def get_config(cls, mode_id):
        return cls.MODES.get(mode_id, cls.MODES["mode_standard_v1"])
    
    @classmethod
    def get_grid_pattern(cls, pattern_id):
        return cls.GRID_PATTERNS.get(pattern_id, cls.GRID_PATTERNS["24-2"])
    
    @classmethod
    def get_test_mode(cls, mode_id):
        return cls.TEST_MODES.get(mode_id, cls.TEST_MODES["standard"])
    
    @classmethod
    def get_test_category(cls, category_id):
        return cls.TEST_CATEGORIES.get(category_id, cls.TEST_CATEGORIES["normal"])