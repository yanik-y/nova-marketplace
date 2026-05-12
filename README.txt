Nova Marketplace — Streamlit + SQLite demo

How to run
==========

1. Open this folder in a terminal.
2. Create a virtual environment:
       python3 -m venv .venv
3. Install dependencies:
       .venv/bin/pip install -r requirements.txt
4. Start the app:
       .venv/bin/streamlit run gw_8.py
5. The app opens at http://localhost:8501

Demo login
==========
Nova mail: 10000@novasbe.pt
Password:  password123

Data
====
- data/                 seed CSVs (users, items, follows, favorites, disposal_locations)
- marketplace.db        SQLite database; created and populated on first run.
                        Delete this file to start fresh from the seed CSVs.
- uploaded_images/      placeholder + user-uploaded item photos
- item_photos/          drop real product photos here, named by item id
                        (see item_photos/README.txt)

Sending this folder to someone
==============================
Zip the project but exclude the virtual environment and the bytecode cache:

    cd ..
    zip -r nova_marketplace.zip uni_marketplace_demo_v6_gw5 \
        -x "uni_marketplace_demo_v6_gw5/.venv/*" \
        -x "uni_marketplace_demo_v6_gw5/__pycache__/*"

The recipient repeats the steps under "How to run" above.
