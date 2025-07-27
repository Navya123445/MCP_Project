import pandas as pd

def add_upselling_reservation_column(input_file, output_file):
    # Read the CSV file
    df = pd.read_csv(input_file)
    
    # Add the new column with default value 'No'
    df['reserved for upselling/season'] = 'No'
    
    # Mark available rooms with price >= 5000 as reserved
    high_end_criteria = (
        (df['Availability'] == 'Available') & 
        (df['Price'] >= 5000)
    )
    
    df.loc[high_end_criteria, 'reserved for upselling/season'] = 'Yes'
    
    # Save the updated CSV file
    df.to_csv(output_file, index=False)
    
    return df

# Usage
add_upselling_reservation_column('Hotel_rooms_updated.csv', 'Hotel_data_updated.csv')
