from dataclasses import dataclass


@dataclass
class Constants:
    """General contants"""
    
    bx_duration:  float = 25          # BX duration in ns
    tdc_duration: float = 25.0 / 30.0 # TDC duration in ns
    orbit_bx:     float = 3564        # number of BX in an orbit
    
    x_cell:       float = 42.0  # cell width  in mm
    z_cell:       float = 13.0  # cell height in mm
    
    x_pos_shift:  tuple = (-9999, -x_cell*7.0, -x_cell*7.5, -x_cell*7.0, -x_cell*7.5)
    z_pos_shift:  tuple = (-9999, -z_cell*1.5, -z_cell*0.5,  z_cell*0.5,  z_cell*1.5)
    
    t_max:        float = 15.6                # max drift time in BX
    t_max_ns:     float = t_max * bx_duration # max drift time in ns
    
    v_drift:      float = x_cell * 0.5 / t_max_ns # drift velocity in mm/ns
    
    ### the following are used as filters to get rid of weird drift times way outside the range of 0-390ns (15.6BX)
    t_drift_min:  float = -50.0
    t_drift_max:  float = 450.0