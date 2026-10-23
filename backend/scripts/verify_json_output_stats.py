import json
from pathlib import Path
from collections import Counter

def count_records(file_path):
    count = 0
    try:
        with file_path.open("r", encoding="utf-8-sig") as stream:
            first = ""
            while not first:
                char = stream.read(1)
                if not char: return 0
                if not char.isspace(): first = char
            stream.seek(0)
            if first == "[":
                parsed = json.load(stream)
                if isinstance(parsed, list):
                    return len(parsed)
            elif first == "{":
                # Could be a single object or JSONL
                try:
                    # Try reading as JSONL first
                    stream.seek(0)
                    lines = 0
                    for line in stream:
                        if line.strip():
                            json.loads(line)
                            lines += 1
                    if lines > 1: return lines
                except json.JSONDecodeError:
                    pass
                # Fallback to single object
                stream.seek(0)
                parsed = json.load(stream)
                if isinstance(parsed, dict): return 1
    except Exception:
        pass
    return 0

root = Path("/home/URK23AI1015/Downloads/final-year-project (2)/json_output")
if not root.exists():
    print(f"Root directory {root} does not exist")
    exit(1)

stats = Counter()
total_files = 0
total_records = 0

# Walk through subdirectories
for subdir in root.iterdir():
    if subdir.is_dir():
        files = list(subdir.rglob("*.json")) + list(subdir.rglob("*.jsonl"))
        subdir_files_count = len(files)
        subdir_records_count = 0
        for f in files:
            subdir_records_count += count_records(f)
        
        print(f"Folder: {subdir.name} | Files: {subdir_files_count} | Records: {subdir_records_count}")
        stats[subdir.name] = subdir_records_count
        total_files += subdir_files_count
        total_records += subdir_records_count

# Also check root files
root_files = list(root.glob("*.json")) + list(root.glob("*.jsonl"))
root_records = sum(count_records(f) for f in root_files)
if root_records > 0:
    print(f"Folder: root | Files: {len(root_files)} | Records: {root_records}")
    total_files += len(root_files)
    total_records += root_records

print("-" * 30)
print(f"Total Files: {total_files}")
print(f"Total Records: {total_records}")
