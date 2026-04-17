import os

# --- Configuration ---
# Point this to your unzipped GitHub repository folder
ROOT_DIR = "." 
OUTPUT_FILE = "pylabcontrol_v2_knowledge.txt"

# Only grab the files we care about for the architecture
ALLOWED_EXTENSIONS = {".py", ".toml", ".md"}

# Folders to completely ignore so we don't waste tokens
IGNORE_DIRS = {".git", "__pycache__", ".venv", "venv", ".vscode", "tests", "docs"}

def consolidate_codebase():
    file_count = 0
    with open(OUTPUT_FILE, "w", encoding="utf-8") as outfile:
        # Add a primer for the Gem at the top of the file
        outfile.write("### PYLABCONTROL ARCHITECTURE REFERENCE ###\n")
        outfile.write("The following is a consolidated codebase containing all active .py and .toml files.\n\n")
        
        for root, dirs, files in os.walk(ROOT_DIR):
            # Modify dirs in-place to skip ignored directories
            dirs[:] = [d for d in dirs if d not in IGNORE_DIRS]

            for file in files:
                ext = os.path.splitext(file)[1].lower()
                if ext in ALLOWED_EXTENSIONS:
                    file_path = os.path.join(root, file)
                    rel_path = os.path.relpath(file_path, ROOT_DIR)
                    
                    # Write clear delimiters that Gemini looks for
                    outfile.write(f"\n{'='*80}\n")
                    outfile.write(f"### FILE: {rel_path} ###\n")
                    outfile.write(f"{'='*80}\n\n")
                    
                    try:
                        with open(file_path, "r", encoding="utf-8") as infile:
                            outfile.write(infile.read())
                            outfile.write("\n")
                            file_count += 1
                    except Exception as e:
                        outfile.write(f"# Error reading file: {e}\n")

    print(f"✅ Success! Packed {file_count} files into {OUTPUT_FILE}.")
    size_mb = os.path.getsize(OUTPUT_FILE) / (1024 * 1024)
    print(f"📁 File size: {size_mb:.2f} MB")

if __name__ == "__main__":
    consolidate_codebase()