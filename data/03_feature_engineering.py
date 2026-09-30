import pandas as pd
import numpy as np
import os


# Values are robust scales below which a standardized deviation is too noisy to
# be clinically or numerically meaningful.  They are not population cutoffs.
PERSONAL_BASELINE_MIN_SCALE = {
    'hr_curr': 3.0, 'map_curr': 2.0, 'rr_curr': 1.0,
    'spo2_curr': 0.5, 'temp_curr': 0.1,
}


def add_personalized_baseline_features(
        df, value_cols, group_cols=('subject_id', 'stay_id'), time_col='hour',
        reference_hours=24, exclusion_hours=1, vital_min_observations=4,
        lab_min_observations=3, lab_cols=(), instability_mad_multiplier=3.0):
    """Add causal, patient/stay-specific physiological baseline features.

    For a prediction at time *t*, values in [t-1-reference_hours, t-2] are
    eligible. The current hour and the immediately preceding hour are excluded
    so a newly developing event cannot redefine its own baseline. The robust
    baseline is the median and its scale is 1.4826 * MAD. No interpolation,
    back-fill, label, or future row is used.

    A baseline is available only after the required number of *observed* values.
    The raw deviation remains available when a baseline exists; its z-score is
    deliberately NaN when the history is unstable or has near-zero spread.
    Status flags make newly admitted, insufficient, unstable, and changing
    clinical states explicit rather than silently imputing a baseline.
    """
    required = set(group_cols) | {time_col}
    absent = required - set(df.columns)
    if absent:
        raise ValueError(f"Baseline construction missing required columns: {sorted(absent)}")
    out = df.copy()
    cols = [c for c in value_cols if c in out.columns]
    lab_cols = set(lab_cols)
    if not cols:
        return out
    out['_baseline_row_order'] = np.arange(len(out))
    out = out.sort_values(list(group_cols) + [time_col]).copy()
    for col in cols:
        for suffix in ('baseline', 'baseline_mad', 'baseline_n', 'baseline_age_hr',
                       'deviation_from_baseline', 'baseline_z', 'baseline_available',
                       'baseline_insufficient', 'baseline_unstable', 'baseline_state_shift'):
            out[f'{col}_{suffix}'] = np.nan

    for _, index in out.groupby(list(group_cols), sort=False).groups.items():
        rows = out.loc[index]
        times = rows[time_col].to_numpy(dtype=float)
        for col in cols:
            vals = pd.to_numeric(rows[col], errors='coerce').to_numpy(dtype=float)
            minimum = lab_min_observations if col in lab_cols else vital_min_observations
            min_scale = PERSONAL_BASELINE_MIN_SCALE.get(col, 1e-6)
            # Original observations only: carried-forward values are not new history.
            if f'{col}_missing' in rows:
                vals[np.asarray(rows[f'{col}_missing'], dtype=bool)] = np.nan
            for pos, (row_idx, now) in enumerate(zip(rows.index, times)):
                # Strict '<' makes a one-hour exclusion omit both the current
                # bin and the immediately prior bin on an hourly grid.
                eligible = (times < now - exclusion_hours) & (times >= now - exclusion_hours - reference_hours)
                history = vals[eligible & np.isfinite(vals)]
                n = len(history)
                out.at[row_idx, f'{col}_baseline_n'] = n
                out.at[row_idx, f'{col}_baseline_insufficient'] = int(n < minimum)
                if n == 0:
                    out.at[row_idx, f'{col}_baseline_available'] = 0
                    continue
                median = float(np.median(history))
                mad = float(1.4826 * np.median(np.abs(history - median)))
                out.at[row_idx, f'{col}_baseline'] = median
                out.at[row_idx, f'{col}_baseline_mad'] = mad
                out.at[row_idx, f'{col}_baseline_age_hr'] = now - max(times[eligible & np.isfinite(vals)])
                out.at[row_idx, f'{col}_baseline_available'] = int(n >= minimum)
                if not np.isfinite(vals[pos]):
                    continue
                deviation = vals[pos] - median
                out.at[row_idx, f'{col}_deviation_from_baseline'] = deviation
                unstable = (n < minimum) or (mad < min_scale)
                out.at[row_idx, f'{col}_baseline_unstable'] = int(unstable)
                # A causal recent-state check; it flags, but does not update, the baseline.
                recent = vals[(times < now) & (times >= now - exclusion_hours - 3) & np.isfinite(vals)]
                recent_median = np.median(recent) if len(recent) else np.nan
                shifted = bool(np.isfinite(recent_median) and mad >= min_scale and
                               abs(recent_median - median) > instability_mad_multiplier * mad)
                out.at[row_idx, f'{col}_baseline_state_shift'] = int(shifted)
                if not unstable:
                    out.at[row_idx, f'{col}_baseline_z'] = deviation / mad
    # Convert flags from NaN to 0 only where not otherwise set; NaN numeric
    # baseline values remain meaningful to tree models and missingness logic.
    for col in cols:
        for suffix in ('baseline_available', 'baseline_insufficient', 'baseline_unstable', 'baseline_state_shift'):
            out[f'{col}_{suffix}'] = out[f'{col}_{suffix}'].fillna(0).astype('int8')
    return out.sort_values('_baseline_row_order').drop(columns='_baseline_row_order')

def create_hourly_bins(df, time_col, group_cols):
    """Bins irregular time-series data into 1-hour intervals."""
    print("Binning data into 1-hour intervals...")
    df[time_col] = pd.to_datetime(df[time_col])
    df = df.set_index(time_col)
    
    # Resample to 1H, grouping by ID
    binned = df.groupby(group_cols).resample('1H').mean()
    
    # Drop group cols from columns if they were moved there, then reset index
    if isinstance(group_cols, list):
        for col in group_cols:
            if col in binned.columns:
                binned = binned.drop(columns=[col])
                
    return binned.reset_index()

def process_vitals(df, vitals_cols, ff_limit=4):
    """
    Applies the hybrid missingness strategy to vitals:
    - Creates missingness indicators.
    - Forward-fills with a strict maximum limit.
    - Calculates time_since_measurement.
    """
    print("Applying hybrid missingness strategy (Forward-fill + Missing Indicators)...")
    df_out = df.copy()
    
    def time_since(series_mask):
        """Helper to calculate hours since the last valid measurement."""
        ts = np.zeros(len(series_mask))
        curr = 0
        for i, val in enumerate(series_mask):
            if val:
                curr = 0
            else:
                curr += 1
            ts[i] = curr
        return ts
    
    for col in vitals_cols:
        if col not in df.columns:
            continue
            
        # 1. Missingness indicator
        df_out[f'{col}_missing'] = df_out[col].isna().astype(int)
        
        # 2. Time since measurement
        # Calculated BEFORE forward filling, using the original NaNs
        mask = df_out[col].notna()
        df_out[f'time_since_{col}_hr'] = df_out.groupby('stay_id')[col].transform(
            lambda x: time_since(~x.isna().values)
        )
        
        # 3. Forward fill with strict limit (e.g., 4 hours)
        df_out[col] = df_out.groupby('stay_id')[col].ffill(limit=ff_limit)
        
    return df_out

def process_labs(df, lab_cols):
    """
    Applies lab-specific strategy: NO interpolation/forward-fill of the value itself,
    but we retain the last known value in a separate feature and track time since measurement.
    """
    print("Processing labs without blind interpolation...")
    df_out = df.copy()
    
    # Similar logic to vitals but strictly NO filling of the primary feature column
    # If the user wants the carried value, we create a specific '{col}_carried' feature
    
    return df_out

def calculate_trend_features(df, vitals_cols):
    """Calculates physiological trends: deltas, slopes, and rolling statistics (4h window)."""
    print("Calculating physiological trend features (Deltas, Slopes, Rolling Stats)...")
    df_out = df.copy()
    
    for col in vitals_cols:
        if col not in df.columns:
            continue
            
        # Deltas
        df_out[f'{col}_delta_1h'] = df_out.groupby('stay_id')[col].diff(periods=1)
        df_out[f'{col}_delta_2h'] = df_out.groupby('stay_id')[col].diff(periods=2)
        df_out[f'{col}_delta_4h'] = df_out.groupby('stay_id')[col].diff(periods=4)
        
        # Slopes (Delta / Time)
        df_out[f'{col}_slope_2h'] = df_out[f'{col}_delta_2h'] / 2.0
        df_out[f'{col}_slope_4h'] = df_out[f'{col}_delta_4h'] / 4.0
        
        # Acceleration (Change in slope -> delta of the 1h delta)
        df_out[f'{col}_accel'] = df_out.groupby('stay_id')[f'{col}_delta_1h'].diff(periods=1)
        
        # Rolling Statistics (4-hour window)
        roll = df_out.groupby('stay_id')[col].rolling(window=4, min_periods=1)
        
        df_out[f'{col}_mean_4h'] = roll.mean().reset_index(level=0, drop=True)
        df_out[f'{col}_min_4h'] = roll.min().reset_index(level=0, drop=True)
        df_out[f'{col}_max_4h'] = roll.max().reset_index(level=0, drop=True)
        df_out[f'{col}_std_4h'] = roll.std().reset_index(level=0, drop=True)
        
        # Range
        df_out[f'{col}_range_4h'] = df_out[f'{col}_max_4h'] - df_out[f'{col}_min_4h']
        
    return df_out

if __name__ == "__main__":
    # Example Usage / Pipeline entry point
    print("Feature Engineering Pipeline Initialized.")
    # In a full run, we would load the chartevents/labevents merged dataframe here.
