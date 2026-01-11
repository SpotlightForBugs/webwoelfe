import sys

# Filter out external package warnings
import warnings

warnings.filterwarnings("ignore")


import sys
import os
import json

# Add the project directory to sys.path
sys.path.append(os.getcwd())

try:
    from roles import RoleRegistry

    print("RoleRegistry imported successfully.")

    roles = RoleRegistry.get_all()
    print(f"RoleRegistry.get_all() returned {len(roles)} roles.")

    # Simulate app.py logic
    grouped_by_extension = {}
    for role in roles:
        print(f"Processing {role.info.name}...")
        ext_pack = role.info.extension_pack
        if ext_pack not in grouped_by_extension:
            grouped_by_extension[ext_pack] = []
        role_dict = role.to_dict()
        # Verify JSON serialization
        try:
            json.dumps(role_dict)
        except TypeError as e:
            print(f"FAILED JSON serialization for {role.info.name}: {e}")
            # Find the culprit
            for k, v in role_dict.items():
                try:
                    json.dumps({k: v})
                except TypeError:
                    print(f"  Field '{k}' is not serializable: {type(v)}")

        grouped_by_extension[ext_pack].append(role_dict)

    print(
        f"Successfully grouped {len(roles)} roles into {len(grouped_by_extension)} extensions."
    )
    print("Extensions found:", list(grouped_by_extension.keys()))

except Exception as e:
    print(f"Error: {e}")
    import traceback

    traceback.print_exc()
