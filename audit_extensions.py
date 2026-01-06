import sys
import os
import warnings

warnings.filterwarnings("ignore")
sys.path.append(os.getcwd())

from roles.registry import RoleRegistry

# Force discovery
import roles

print(f"{'Role Name':<30} | {'Current Extension':<20}")
print("-" * 55)

counts = {}

# Get all roles and sort by extension then name
all_roles = RoleRegistry.get_all()
sorted_roles = sorted(all_roles, key=lambda r: (r.info.extension_pack, r.info.name))

for role in sorted_roles:
    name = role.info.name
    ext = role.info.extension_pack
    print(f"{name:<30} | {ext:<20}")

    counts[ext] = counts.get(ext, 0) + 1

print("\nCounts:")
for k, v in counts.items():
    print(f"{k}: {v}")
