from dataclasses import dataclass, field
import numpy as np


@dataclass
class SLConfig:
    """Configuration of SuperLayers"""
    
    sl_shift: dict = field(default_factory=lambda: {
        0: {"x":0, "y":0, "z":364.75},
        1: {"x":0, "y":0, "z":529.75},
        2: {"x":0, "y":0, "z":695.75},
        3: {"x":0, "y":0, "z":790.75}
    })
    
    sl_view: dict = field(default_factory=lambda: {
        0: "phi",
        1: "phi",
        2: "phi",
        3: "phi"
    })
    
    sl_mapping: dict = field(default_factory=lambda: {
        0: {"fpga":0, "ch_start":0,  "ch_end":63},
        1: {"fpga":0, "ch_start":64, "ch_end":127},
        2: {"fpga":1, "ch_start":0,  "ch_end":63},
        3: {"fpga":1, "ch_start":64, "ch_end":127},
    })
    
    time_offset: dict = field(default_factory=lambda: {
        0: -2.3,
        1:  2.2,
        2: -14.5,
        3: -4.3
    })
    

@dataclass
class DataConfig:
    """Data stream configuration"""
    
    data_dir: str 
    
    data_type: dict = field(default_factory=lambda: {
        "HEAD":        np.uint8,
        "FPGA":        np.uint8,
        "TDC_CHANNEL": np.uint8,
        "ORBIT_CNT":   np.uint64,
        "BX_COUNTER":  np.uint16,
        "TDC_MEAS":    np.uint8,
    })
    
    valid_hit_header: int = 2
    
    scint_row: dict = field(default_factory=lambda: {
        "head":2, "fpga":1, "tdc_ch": 128
    })
    
    time_offset_scint: float = 144.35
    
    