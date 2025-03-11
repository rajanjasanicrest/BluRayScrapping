import json

# Load existing JSON data
with open("data/DVD-1998.json", "r", encoding="utf-8") as f:
    existing_data = json.load(f)

# Use a set to track unique (title, sku) pairs
seen = []
unique_data = []
for item in existing_data:
    if item:
        bluray_url = item.get("blu_ray_url", "")


        if bluray_url not in seen:
            seen.append(bluray_url)
            unique_data.append(item)  # Keep only unique entries

        # if 'production_year' in item.keys():
        #     unique_data.append(item)

# Save the filtered unique data back to the JSON file
with open("data/DVD-1998.json", "w", encoding="utf-8") as f:
    json.dump(unique_data, f, indent=4)

print("Duplicates removed based on title and SKU.")