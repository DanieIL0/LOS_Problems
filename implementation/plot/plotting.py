import matplotlib.pyplot as plt
import os
from datetime import datetime, timedelta
import pandas as pd 
import numpy as np 

def plot_data(summary_df, min_timestamp, max_timestamp, results_path):
    """
    Plots the missing percentage of telescope data over time.

    Parameters:
        summary_df (pandas.DataFrame): Summary data containing the missing percentages.
        min_timestamp (float): Minimum timestamp for the x-axis.
        max_timestamp (float): Maximum timestamp for the x-axis.
        results_path (str): Directory where the plot will be saved.
    """
    # Check if summary_df is empty for example if timestamps don't align
    if summary_df.empty:
        print("The summary is empty")
        return
    
    if 'File' not in summary_df.columns or 'Telescope Missing Percentage' not in summary_df.columns:
        print("The DataFrame misses columns")
        return
    
    summary_df['Time'] = pd.to_datetime(
        summary_df['File'].str.extract(r'(\d{4}-\d{2}-\d{2}-\d{2}-\d{2}-\d{2})')[0],
        format='%Y-%m-%d-%H-%M-%S'
    )
    summary_df = summary_df.sort_values('Time').reset_index(drop=True)
    
    plt.figure(figsize=(12, 6))
    
    time_gap_threshold = timedelta(minutes=2) 

    for i in range(1, len(summary_df)):
        time_diff = summary_df.loc[i, 'Time'] - summary_df.loc[i - 1, 'Time']
        if time_diff <= time_gap_threshold:
            plt.plot(
                summary_df.loc[i-1:i, 'Time'],
                summary_df.loc[i-1:i, 'Telescope Missing Percentage'],
                marker='o', linestyle='-', color='red', label='_nolegend_'
            )

    plt.xlabel('Time')
    plt.ylabel('Missing Percentage')

    # Use min and max timestamps for ticks
    if min_timestamp is not None and max_timestamp is not None:
        num_ticks = min(10, len(summary_df))  # Ensure x-axis is not crowded
        ticks = np.linspace(min_timestamp, max_timestamp, num=num_ticks)
        tick_labels = [datetime.fromtimestamp(t).strftime('%H:%M') for t in ticks]
        plt.xticks(
            ticks=[datetime.fromtimestamp(t) for t in ticks],
            labels=tick_labels,
            rotation=45
        )

    plt.title('Telescope Missing Percentage')
    plt.grid(True)
    plt.tight_layout()
    plot_output = os.path.join(results_path, 'filtered_telescope_missing_percentage_plot.png')
    plt.savefig(plot_output)
    plt.show()