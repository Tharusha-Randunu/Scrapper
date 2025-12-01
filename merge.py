import pandas as pd
import glob
import os

# Define the folder containing your CSV files
csv_folder = "2025 CSVs"

# Check if folder exists
if not os.path.exists(csv_folder):
    print(f"ERROR: Folder '{csv_folder}' not found!")
    print(f"Current directory: {os.getcwd()}")
    print(f"Available folders/files: {os.listdir('.')}")
    exit()

# Change to the CSV folder
original_dir = os.getcwd()
os.chdir(csv_folder)
print(f"Changed to directory: {os.getcwd()}")

# Pattern to match all your CSV files
csv_files = glob.glob("*.csv")  # Get ALL CSV files

# If you want only 2024 files, try these patterns:
# csv_files = glob.glob("2024*.csv")
# csv_files = glob.glob("*2024*.csv")

print(f"Files found in '{csv_folder}': {csv_files}")

# Check if files were found
if not csv_files:
    print(f"No CSV files found in '{csv_folder}'!")
    print(f"Files in '{csv_folder}': {os.listdir('.')}")
    os.chdir(original_dir)  # Change back
    exit()

# Read and combine
df_list = []
for file in csv_files:
    try:
        df = pd.read_csv(file)
        print(f"Read {file}: {len(df)} rows, {len(df.columns)} columns")
        df_list.append(df)
    except Exception as e:
        print(f"Error reading {file}: {e}")

if not df_list:
    print("No dataframes were successfully read!")
    os.chdir(original_dir)
    exit()

merged_df = pd.concat(df_list, ignore_index=True)

print(f"\nInitial total rows after merging: {len(merged_df)}")
print(f"Columns: {list(merged_df.columns)}")

# TYPE 1: Remove duplicates with the same jobref
if 'jobref' in merged_df.columns:
    jobref_duplicates = merged_df['jobref'].duplicated().sum()
    print(f"\nDuplicate jobrefs found: {jobref_duplicates}")
    
    # Keep the first occurrence of each jobref
    merged_df.drop_duplicates(subset=["jobref"], keep='first', inplace=True)
    print(f"Removed {jobref_duplicates} rows with duplicate jobref")
    print(f"Rows after jobref deduplication: {len(merged_df)}")
else:
    print("Warning: 'jobref' column not found.")

# TYPE 2: Remove duplicates where all OTHER columns are the same (ignoring page, row_no, jobref)
# Define the columns to check for duplicates (excluding the first three)
columns_to_check = ['position', 'company', 'jobdesc_snippet', 'opening_date', 
                    'closing_date', 'town', 'row_type']

# Check which of these columns actually exist in your dataframe
existing_columns = [col for col in columns_to_check if col in merged_df.columns]
print(f"\nChecking duplicates based on columns: {existing_columns}")

if existing_columns:
    # Count duplicates based on these columns
    content_duplicates = merged_df.duplicated(subset=existing_columns, keep=False).sum()
    print(f"Rows with duplicate content (same position, company, etc.): {content_duplicates}")
    
    if content_duplicates > 0:
        print("\nSample of duplicate content (keeping first occurrence of each):")
        
        # Mark duplicates and show examples
        merged_df['is_duplicate_content'] = merged_df.duplicated(subset=existing_columns, keep='first')
        
        # Show some examples
        duplicate_samples = merged_df[merged_df['is_duplicate_content']].head(3)
        if len(duplicate_samples) > 0:
            for idx, row in duplicate_samples.iterrows():
                print(f"  - Position: '{row.get('position', 'N/A')}', Company: '{row.get('company', 'N/A')}', "
                      f"Town: '{row.get('town', 'N/A')}', JobRef: {row.get('jobref', 'N/A')}")
        
        # Remove the temporary column
        merged_df = merged_df.drop(columns=['is_duplicate_content'])
        
        # Remove the duplicates, keeping only the first occurrence
        before_count = len(merged_df)
        merged_df.drop_duplicates(subset=existing_columns, keep='first', inplace=True)
        content_removed = before_count - len(merged_df)
        print(f"\nRemoved {content_removed} rows with duplicate content")
        print(f"Rows after content deduplication: {len(merged_df)}")

# Alternative: Check for EXACT duplicates in all columns (optional)
print(f"\nChecking for exact duplicates in ALL columns...")
exact_duplicates = merged_df.duplicated().sum()
if exact_duplicates > 0:
    print(f"Found {exact_duplicates} exact duplicate rows (all columns identical)")
    merged_df.drop_duplicates(inplace=True)
    print(f"Rows after removing exact duplicates: {len(merged_df)}")

# Change back to original directory before saving
os.chdir(original_dir)

# Save combined file
output_filename = "2025_merged.csv"
merged_df.to_csv(output_filename, index=False, encoding="utf-8-sig")

print("\n" + "="*50)
print("DUPLICATE REMOVAL SUMMARY")
print("="*50)
initial_total = sum(len(df) for df in df_list)
final_total = len(merged_df)
removed_total = initial_total - final_total

print(f"Total rows in original files: {initial_total}")
print(f"Total rows after duplicate removal: {final_total}")
print(f"Total duplicates removed: {removed_total}")
print(f"Duplicate removal rate: {removed_total/initial_total*100:.1f}%")
print(f"\nMerged and deduplicated CSV saved as: {output_filename}")
print("="*50)

# Optional: Show first few rows of the final dataframe
print("\nFirst 3 rows of final merged data:")
print(merged_df.head(3).to_string())