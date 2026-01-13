
import sys
import os
sys.path.append(os.getcwd())
from app import app
from roles import RoleRegistry

with app.app_context():
    role = RoleRegistry.get("Aurenseherin")
    if role:
        print("Role found:", role.info.name)
        ui = role.get_ui_definition()
        print("UI Definition buttons:", [b.label for b in ui.buttons])
    else:
        print("Role NOT found")
