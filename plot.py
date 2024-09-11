import pandas as pd
import os
from implementation.shared.config import RESULTS_DIR_PLOT
from implementation.plot.data_processing import extract_data_from_bag
from implementation.plot.plotting import plot_data

# Run the data extraction and processing
summary_data, min_timestamp, max_timestamp = extract_data_from_bag()

# Create a summary DataFrame and save it
if summary_data:  # Ensure there is data before saving
    summary_df = pd.DataFrame(summary_data)
    summary_csv_path = os.path.join(RESULTS_DIR_PLOT, 'ar_tracking_summary.csv')
    summary_df.to_csv(summary_csv_path, index=False)
    print(f"Summary table saved to {summary_csv_path}")

    # Calculate and print the average missing percentage for the telescope
    # Filter only telescope data
    telescope_data = summary_df[summary_df['Total Telescope Points'] > 0]
    average_missing_percentage = telescope_data['Telescope Missing Percentage'].mean()
    print(f"[INFO] Average Telescope Missing Percentage: {average_missing_percentage:.2f}%")

    # Now perform the analysis and plotting of the filtered summary data
    plot_data(telescope_data, min_timestamp, max_timestamp, RESULTS_DIR_PLOT)
else:
    print("No data was processed. Summary table will not be created.")
    exit()
