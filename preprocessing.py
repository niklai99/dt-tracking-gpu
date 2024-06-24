import os
from typing import Callable
import cudf
import cupy as cp
from Configurations import DataConfig, SLConfig
from Constants import Constants
import time
import argparse


def read_data(config: DataConfig, n_files: int):
    """Read data from files."""
    file_list = os.listdir(config.data_dir)[:n_files] if n_files > 0 else os.listdir(config.data_dir)
    
    if file_list[0].endswith(".csv"):
        # print("Reading CSV files")
        data_frames = [cudf.read_csv(os.path.join(config.data_dir, file), dtype=config.data_type) for file in file_list]
    elif file_list[0].endswith(".parquet"):
        # print("Reading Parquet files")
        data_frames = [cudf.read_parquet(os.path.join(config.data_dir, file)) for file in file_list]
        data_frames = [df.astype(config.data_type) for df in data_frames]
    
    return cudf.concat(data_frames)


def split_data_scint(data: cudf.DataFrame, config: DataConfig):
    """Split data into hits and scintillator data."""
    hits_df = data[(data["HEAD"] == config.valid_hit_header) & (data["TDC_CHANNEL"] < 128)]
    scintillator_df = data[
        (data["HEAD"] == config.scint_row["head"]) &
        (data["FPGA"] == config.scint_row["fpga"]) &
        (data["TDC_CHANNEL"] == config.scint_row["tdc_ch"])
    ]
    
    return hits_df, scintillator_df


def convert_tdc_to_ns(data: cudf.DataFrame, col: str, constants: Constants):
    """Convert TDC time to nanoseconds."""
    data[col] = (data["BX_COUNTER"] * constants.bx_duration) + (data["TDC_MEAS"] * constants.tdc_duration)
    return data


def select_hits_within_orbit(hits_df: cudf.DataFrame, scint_df: cudf.DataFrame, config: DataConfig):
    """Select hits within the same orbit as the scintillator trigger."""
    merged_df = cudf.merge(
        hits_df[["FPGA", "TDC_CHANNEL", "ORBIT_CNT", "tdc_ns"]],
        scint_df[["ORBIT_CNT", "t0_ns"]],
        on="ORBIT_CNT"
    )
    
    merged_df["t_drift"] = merged_df["tdc_ns"] - merged_df["t0_ns"] + config.time_offset_scint
    valid_hits = merged_df[(merged_df["t_drift"] > Constants.t_drift_min) & (merged_df["t_drift"] < Constants.t_drift_max)]
    
    return valid_hits.drop(["tdc_ns"], axis=1)


def assign_super_layer(data: cudf.DataFrame, config: SLConfig):
    """Assign super layer to each hit."""
    data["SL"] = -1  # Initialize super layer column with -1
    
    for sl, sl_cfg in config.sl_mapping.items():
        mask = (
            (data["FPGA"] == sl_cfg["fpga"]) &
            (data["TDC_CHANNEL"] >= sl_cfg["ch_start"]) &
            (data["TDC_CHANNEL"] <= sl_cfg["ch_end"])
        )
        data.loc[mask, "SL"] = sl

    return data.astype({"SL": "uint8"})


def assign_layer(data: cudf.DataFrame):
    """Assign layer to each hit based on TDC channel modulo operation."""
    data["LAYER"] = -1
    
    data.loc[(data["TDC_CHANNEL"] % 4 == 0), "LAYER"] = 4
    data.loc[(data["TDC_CHANNEL"] % 4 == 2), "LAYER"] = 3
    data.loc[(data["TDC_CHANNEL"] % 4 == 1), "LAYER"] = 2
    data.loc[(data["TDC_CHANNEL"] % 4 == 3), "LAYER"] = 1
    
    return data.astype({"LAYER": "uint8"})


def shift_tdc_channels(data: cudf.DataFrame, config: SLConfig):
    """Shift TDC channels to start from 0 for each super layer."""
    for sl in range(4):
        mask = data["SL"] == sl
        data.loc[mask, "TDC_CHANNEL"] -= config.sl_mapping[sl]["ch_start"]

    return data


def assign_layer_and_sl(data: cudf.DataFrame, config: SLConfig):
    """Assign layer and super layer to each hit."""
    data = assign_super_layer(data, config)
    data = assign_layer(data)
    data = shift_tdc_channels(data, config)
    return data


def select_hits_by_super_layer(data: cudf.DataFrame, super_layer: int):
    """Select hits from a specific super layer."""
    return data[data["SL"] == super_layer]


def select_hits_by_macrocell(data: cudf.DataFrame, ch_start: int, ch_end: int):
    """Select hits from a specific macrocell."""
    return data[(data["TDC_CHANNEL"] >= ch_start) & (data["TDC_CHANNEL"] < ch_end)]


def convert_to_local_coords(data: cudf.DataFrame, constants: Constants):
    """Convert TDC channel to local coordinates."""
    data["WIRE_X_LOC"] = 0
    data["WIRE_Z_LOC"] = 0
    
    for layer in [1, 2, 3, 4]:
        mask = data["LAYER"] == layer
        data.loc[mask, "WIRE_X_LOC"] = (data["TDC_CHANNEL"] % 64 // 4) * constants.x_cell + constants.x_pos_shift[layer]
        data.loc[mask, "WIRE_Z_LOC"] = constants.z_pos_shift[layer]
    
    return data


def convert_to_global_coords(data: cudf.DataFrame, config: SLConfig, time_shift: float = 0):
    """Convert local coordinates to global coordinates."""
    data["WIRE_X_GLOB"] = 0
    data["WIRE_Z_GLOB"] = 0
    
    for sl, shift in config.sl_shift.items():
        mask = data["SL"] == sl
        data.loc[mask, "WIRE_Z_GLOB"] = data["WIRE_Z_LOC"] + shift["z"]
        data.loc[mask, "WIRE_X_GLOB"] = data["WIRE_X_LOC"] + shift["x"]

    for sl, offset in config.time_offset.items():
        data.loc[data["SL"] == sl, "t0_ns"] -= offset - time_shift

    return data.drop(["WIRE_X_LOC", "WIRE_Z_LOC"], axis=1)


def map_to_global(data: cudf.DataFrame, config: SLConfig, constants: Constants, time_shift: float = 0):
    """Map TDC channel to global coordinates."""
    data = convert_to_local_coords(data, constants)
    data = convert_to_global_coords(data, config, time_shift)
    return data


def compute_hit_positions(data: cudf.DataFrame, constants: Constants):
    """Compute the hit positions in the global coordinate system."""
    data["X_LEFT"] = data["WIRE_X_GLOB"] - data["t_drift"] * constants.v_drift
    data["X_RIGHT"] = data["WIRE_X_GLOB"] + data["t_drift"] * constants.v_drift
    
    return data


def parse_arguments():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description="Run the analysis")
    parser.add_argument("--n", type=int, default=-1, help="Number of files to read")
    parser.add_argument("--run_shift", type=float, default=0, help="Run time shift")
    return parser.parse_args()


def evaluate_performance(func: Callable, n_repetitions: int, **kwargs):
    """Evaluate the performance of a callable function."""
    times = []

    for _ in range(n_repetitions):
        start_time = time.time()
        func(**kwargs)
        end_time = time.time()
        times.append(end_time - start_time)
    
    times = cp.array(times)
    avg_time = cp.mean(times)
    std_time = cp.std(times)
    
    print(f"Average time: {avg_time:.5f} +/- {std_time:.5f} s computed over {n_repetitions} repetitions\n")
    return avg_time, std_time


def main(n_files: int = -1, run_time_shift: float = 0):
    """Main function to run the analysis."""
    constants   = Constants()
    data_config = DataConfig(data_dir="../run000085all/")
    sl_config   = SLConfig()
    
    # Load and preprocess data
    raw_data = read_data(data_config, n_files)
    hits_df, scint_df = split_data_scint(raw_data, data_config)
    
    scint_df = convert_tdc_to_ns(scint_df, "t0_ns", constants)
    hits_df  = convert_tdc_to_ns(hits_df, "tdc_ns", constants)
    
    hits_df = select_hits_within_orbit(hits_df, scint_df, data_config)
    hits_df = assign_layer_and_sl(hits_df, sl_config)
    
    hits_df = select_hits_by_super_layer(hits_df, 1)
    hits_df = select_hits_by_macrocell(hits_df, 8, 36)
    
    hits_df = map_to_global(hits_df, sl_config, constants, run_time_shift)
    hits_df = compute_hit_positions(hits_df, constants)
    

if __name__ == "__main__":
    args = parse_arguments()
    main(n_files=args.n, run_time_shift=args.run_shift)
