"""
AI Count Forecaster

Created by: Pratik Das
Date: 2025-10-21
Version: 1.0
"""

import os
import argparse
import warnings
from datetime import timedelta
import pandas as pd
import numpy as np
from dotenv import load_dotenv
from sklearn.ensemble import RandomForestRegressor

warnings.filterwarnings('ignore')

load_dotenv()

# Directories
current_dir = os.getcwd()
# Get the parent directory
parent_dir = os.path.dirname(current_dir)

INPUT_DIR = os.path.join(parent_dir, os.getenv("INPUT_DIR"))
OUTPUT_DIR = os.path.join(parent_dir, os.getenv("OUTPUT_DIR"))

# Define working hours by day of week
WORKING_HOURS = {
    0: (5, 0, 21, 0),   # Monday: 5:00 AM - 9:00 PM
    1: (5, 0, 21, 0),   # Tuesday: 5:00 AM - 9:00 PM
    2: (5, 0, 21, 0),   # Wednesday: 5:00 AM - 9:00 PM
    3: (5, 0, 21, 0),   # Thursday: 5:00 AM - 9:00 PM
    4: (7, 0, 21, 0),   # Friday: 7:00 AM - 9:00 PM
    5: (6, 0, 19, 0),   # Saturday: 6:00 AM - 7:00 PM
    6: (6, 0, 19, 0),   # Sunday: 6:00 AM - 7:00 PM
}

def is_working_hour(timestamp):
    """Check if timestamp is within working hours"""
    day_of_week = timestamp.weekday()
    start_hour, start_min, end_hour, end_min = WORKING_HOURS[day_of_week]
    
    time_of_day = timestamp.replace(second=0, microsecond=0)
    start_time = timestamp.replace(hour=start_hour, minute=start_min, second=0, microsecond=0)
    end_time = timestamp.replace(hour=end_hour, minute=end_min, second=0, microsecond=0)
    
    return start_time <= time_of_day < end_time

def get_working_hours_only(df):
    """Filter to only working hours"""
    df = df.copy()
    df['timestamp'] = pd.to_datetime(df['timestamp'])
    df['is_working'] = df['timestamp'].apply(is_working_hour)
    return df[df['is_working']].drop('is_working', axis=1).reset_index(drop=True)

def get_next_day_working_hours(last_timestamp):
    """Get all working hours for the next calendar day"""
    # Move to the next day
    next_day = (last_timestamp + timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
    
    forecast_hours = []
    current = next_day
    end_of_day = next_day + timedelta(days=1)
    
    while current < end_of_day:
        if is_working_hour(current):
            forecast_hours.append(current)
        current += timedelta(hours=1)
    
    return forecast_hours

def create_features(df):
    """Create time-based features from timestamp"""
    df = df.copy()
    
    # Basic datetime features
    df['day'] = df['timestamp'].dt.day
    df['hour'] = df['timestamp'].dt.hour
    df['day_of_week'] = df['timestamp'].dt.dayofweek  # Monday=0, Sunday=6
    df['is_weekend'] = df['day_of_week'].isin([5, 6]).astype(int)  # Saturday, Sunday
    # df['month'] = df['timestamp'].dt.month
    # df['day_of_month'] = df['timestamp'].dt.day
    # df['week_of_year'] = df['timestamp'].dt.isocalendar().week

    
    return df

def create_lag_features(df, target_col, lags=[1, 2, 3, 24, 48]):
    """Create lag features for time series"""
    df = df.copy()
    
    for lag in lags:
        df[f'{target_col}_lag_{lag}'] = df[target_col].shift(lag)
    
    # Rolling statistics
    df[f'{target_col}_rolling_mean_3'] = df[target_col].shift(1).rolling(window=3, min_periods=1).mean()
    df[f'{target_col}_rolling_mean_24'] = df[target_col].shift(1).rolling(window=24, min_periods=1).mean()
    df[f'{target_col}_rolling_std_24'] = df[target_col].shift(1).rolling(window=24, min_periods=1).std()
    
    return df

def parse_arguments():
    parser = argparse.ArgumentParser(description='Forecast hourly counts for the next day using Random Forest')
    parser.add_argument('csv', type=str, help='Path to the count CSV file')
    parser.add_argument('--output', type=str, default=None, help='Path to save the forecast CSV (optional)')
    parser.add_argument('--n_estimators', type=int, default=500, help='Number of trees in Random Forest')
    return parser.parse_args()

def get_output_path(input_csv, output_csv):
    """Determine output file path"""
    if output_csv:
        return output_csv
    
    os.makedirs('output', exist_ok=True)
    filename = os.path.basename(input_csv)
    base_name, ext = os.path.splitext(filename)
    output_filename = f'{base_name}_forecast.csv'
    return os.path.join(OUTPUT_DIR, output_filename)

def forecast_random_forest(df_working, target_col, forecast_timestamps, n_estimators=100):
    """Forecast using Random Forest Regressor"""
    try:
        # Create features for training data
        df_train = create_features(df_working)
        # df_train = create_lag_features(df_train, target_col)
        
        # Drop rows with NaN (from lag features)
        df_train_clean = df_train.dropna()
        
        if len(df_train_clean) < 10:
            print(f"    Not enough data after creating lag features")
            return None
        
        # Define feature columns
        feature_cols = ['day', 'hour', 'day_of_week', 'is_weekend',] # 'month', 'day_of_month', 'week_of_year']
        
        # Prepare training data
        X_train = df_train_clean[feature_cols]
        y_train = df_train_clean[target_col]
        
        # Train Random Forest
        model = RandomForestRegressor(
            n_estimators=n_estimators,
            max_depth=15,
            min_samples_split=5,
            min_samples_leaf=2,
            random_state=42,
            n_jobs=-1
        )
        
        model.fit(X_train, y_train)
        
        # Prepare forecast data
        forecast_df = pd.DataFrame({'timestamp': forecast_timestamps})
        forecast_df = create_features(forecast_df)
        
        # Create a combined dataframe for lag feature generation
        combined_df = pd.concat([
            df_working[['timestamp', target_col]],
            forecast_df[['timestamp']].assign(**{target_col: np.nan})
        ], ignore_index=True)
        
        combined_df = create_features(combined_df)
        # combined_df = create_lag_features(combined_df, target_col)
        
        # Extract forecast rows
        forecast_with_lags = combined_df.iloc[-len(forecast_timestamps):].copy()
        
        # Make predictions
        X_forecast = forecast_with_lags[feature_cols]
        predictions = model.predict(X_forecast)
        
        # Get feature importance
        feature_importance = pd.DataFrame({
            'feature': feature_cols,
            'importance': model.feature_importances_
        }).sort_values('importance', ascending=False)
        
        print(f"    Top 5 features: {', '.join(feature_importance.head(5)['feature'].tolist())}")
        
        return np.maximum(predictions, 0)  # Ensure non-negative
        
    except Exception as e:
        print(f"    Random Forest failed: {str(e)}")
        import traceback
        traceback.print_exc()
        return None

def forecast_simple_average(series, forecast_length, seasonal_period=24):
    """Simple seasonal average fallback method"""
    if len(series) >= seasonal_period:
        last_period = series[-seasonal_period:]
        n_repeats = (forecast_length // seasonal_period) + 1
        forecast = np.tile(last_period, n_repeats)[:forecast_length]
    else:
        forecast = np.full(forecast_length, series.mean())
    
    return np.maximum(forecast, 0)

def forecast_data(input_csv, output_csv, n_estimators=100):
    """Main forecasting function"""
    
    if not os.path.exists(input_csv):
        raise FileNotFoundError(f"Input CSV file not found: {input_csv}")
    
    print(f"Reading input file: {input_csv}")
    
    # Read and aggregate to hourly
    df = pd.read_csv(input_csv, usecols=['timestamp', 'incoming_last_interval', 'outgoing_last_interval'])
    df['timestamp'] = pd.to_datetime(df['timestamp'])
    
    print(f"Aggregating data to hourly level...")
    df_hourly = df.set_index('timestamp').resample('H').sum().reset_index()
    df_hourly.columns = ['timestamp', 'incoming_last_interval', 'outgoing_last_interval']
    
    # Filter to working hours only
    print("Filtering to working hours only...")
    df_working = get_working_hours_only(df_hourly)
    
    print(f"Data prepared. Total working hours: {len(df_working)}")
    print(f"Date range: {df_working['timestamp'].min()} to {df_working['timestamp'].max()}")
    
    # Get last timestamp and forecast hours for NEXT DAY only
    last_timestamp = df_working['timestamp'].max()
    forecast_hours = get_next_day_working_hours(last_timestamp)
    forecast_length = len(forecast_hours)
    
    next_day_date = (last_timestamp + timedelta(days=1)).date()
    print(f"\nForecasting for next day: {next_day_date}")
    print(f"Total working hours to forecast: {forecast_length}")
    print(f"Time range: {forecast_hours[0].strftime('%Y-%m-%d %H:%M')} to {forecast_hours[-1].strftime('%Y-%m-%d %H:%M')}")
    print(f"Using model: Random Forest Regressor (n_estimators={n_estimators})")
    
    # Dictionary to store forecasts
    forecasts_dict = {}
    
    print("\nForecasting each column...")
    
    # Forecast each column
    for col in ['incoming_last_interval', 'outgoing_last_interval']:
        print(f"  Processing: {col}")
        
        # Use Random Forest
        forecast_values = forecast_random_forest(
            df_working[['timestamp', col]], 
            col, 
            forecast_hours,
            n_estimators
        )
        
        # Fallback if Random Forest fails
        if forecast_values is None:
            print(f"    Using fallback method for {col}")
            series = df_working[col].values
            forecast_values = forecast_simple_average(series, forecast_length)
        
        forecasts_dict[col] = pd.DataFrame({
            'timestamp': forecast_hours,
            col: forecast_values
        })
        
        print(f"    ✓ Completed: {col} (mean: {forecast_values.mean():.1f}, std: {forecast_values.std():.1f})")
    
    print("\nCombining forecasts...")
    
    # Combine all forecasts
    result = forecasts_dict['incoming_last_interval'].copy()
    result = result.merge(forecasts_dict['outgoing_last_interval'], on='timestamp')
    
    # Round to integers
    for col in ['incoming_last_interval', 'outgoing_last_interval']:
        result[col] = result[col].round(0).astype(int)
    
    # Determine output path
    output_path = get_output_path(input_csv, output_csv)
    
    # Save to CSV
    result.to_csv(output_path, index=False)
    print(f"\n✓ Forecast completed and saved to: {output_path}")
    # print(f"\nForecast summary:")
    # print(result)
    # print(f"\nSummary statistics:")
    # print(result[['incoming_last_interval', 'outgoing_last_interval']].describe())

if __name__ == '__main__':
    args = parse_arguments()
    
    try:
        forecast_data(args.csv, args.output, args.n_estimators)
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        exit(1)