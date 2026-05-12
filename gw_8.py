import streamlit as st
import sqlite3
import hashlib
import os
import csv
import pandas as pd
import pydeck as pdk
from datetime import datetime, timedelta

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_NAME = os.path.join(BASE_DIR, "marketplace.db")
IMAGE_FOLDER = os.path.join(BASE_DIR, "uploaded_images")
ITEM_PHOTOS_FOLDER = os.path.join(BASE_DIR, "item_photos")
DATA_FOLDER = os.path.join(BASE_DIR, "data")

CATEGORIES = ["clothes", "electronics", "books", "furniture", "kitchen", "sports", "school supplies", "decoration", "other"]

os.makedirs(IMAGE_FOLDER, exist_ok=True)
os.makedirs(ITEM_PHOTOS_FOLDER, exist_ok=True)


def connect_db():
    return sqlite3.connect(DB_NAME)


def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()


def create_tables():
    conn = connect_db()
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            username TEXT PRIMARY KEY,
            first_name TEXT,
            last_name TEXT,
            birthdate TEXT,
            nova_mail TEXT,
            password TEXT
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT,
            description TEXT,
            category TEXT,
            price INTEGER,
            seller_username TEXT,
            post_type TEXT,
            created_at TEXT,
            image_path TEXT,
            status TEXT DEFAULT 'available'
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS follows (
            follower_username TEXT,
            followed_username TEXT
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS favorites (
            username TEXT,
            item_id INTEGER
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS disposal_locations (
            id INTEGER PRIMARY KEY,
            name TEXT,
            location_type TEXT,
            category TEXT,
            address TEXT,
            website TEXT,
            latitude REAL,
            longitude REAL,
            opening_hours TEXT,
            description TEXT,
            maps_url TEXT
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS conversations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            item_id INTEGER,
            buyer_username TEXT,
            seller_username TEXT,
            created_at TEXT,
            UNIQUE (item_id, buyer_username, seller_username)
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            conversation_id INTEGER,
            sender_username TEXT,
            body TEXT,
            sent_at TEXT,
            read_at TEXT
        )
    """)

    try:
        cursor.execute("ALTER TABLE items ADD COLUMN end_time TEXT")
    except sqlite3.OperationalError:
        pass

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS bids (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            item_id INTEGER,
            bidder_username TEXT,
            amount INTEGER,
            created_at TEXT
        )
    """)

    conn.commit()
    conn.close()


def table_is_empty(table_name):
    conn = connect_db()
    cursor = conn.cursor()
    cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
    count = cursor.fetchone()[0]
    conn.close()
    return count == 0


def import_demo_data():
    if not table_is_empty("users"):
        return

    conn = connect_db()
    cursor = conn.cursor()

    with open(os.path.join(DATA_FOLDER, "users.csv"), newline="", encoding="utf-8") as file:
        reader = csv.DictReader(file)
        for row in reader:
            nova_mail = row["nova_mail"].lower().strip()
            cursor.execute("""
                INSERT OR IGNORE INTO users
                (username, first_name, last_name, birthdate, nova_mail, password)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                nova_mail,
                row["first_name"],
                row["last_name"],
                row["birthdate"],
                nova_mail,
                hash_password(row["password"])
            ))

    with open(os.path.join(DATA_FOLDER, "items.csv"), newline="", encoding="utf-8") as file:
        reader = csv.DictReader(file)
        for row in reader:
            cursor.execute("""
                INSERT OR IGNORE INTO items
                (id, title, description, category, price, seller_username, post_type, created_at, image_path, status)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                int(row["id"]),
                row["title"],
                row["description"],
                row["category"],
                int(row["price"]),
                row["seller_username"].lower().strip(),
                row["post_type"],
                row["created_at"],
                row["image_path"],
                row["status"]
            ))

    with open(os.path.join(DATA_FOLDER, "follows.csv"), newline="", encoding="utf-8") as file:
        reader = csv.DictReader(file)
        for row in reader:
            cursor.execute("""
                INSERT INTO follows (follower_username, followed_username)
                VALUES (?, ?)
            """, (row["follower_username"].lower().strip(), row["followed_username"].lower().strip()))

    with open(os.path.join(DATA_FOLDER, "favorites.csv"), newline="", encoding="utf-8") as file:
        reader = csv.DictReader(file)
        for row in reader:
            cursor.execute("""
                INSERT INTO favorites (username, item_id)
                VALUES (?, ?)
            """, (row["username"].lower().strip(), int(row["item_id"])))

    conn.commit()
    conn.close()


def import_disposal_data():
    if not table_is_empty("disposal_locations"):
        return

    csv_path = os.path.join(DATA_FOLDER, "disposal_locations.csv")
    if not os.path.exists(csv_path):
        return

    conn = connect_db()
    cursor = conn.cursor()

    with open(csv_path, newline="", encoding="utf-8") as file:
        reader = csv.DictReader(file)
        for row in reader:
            lat = row.get("latitude", "").strip()
            lon = row.get("longitude", "").strip()
            latitude = float(lat) if lat != "" else None
            longitude = float(lon) if lon != "" else None

            cursor.execute("""
                INSERT OR IGNORE INTO disposal_locations
                (id, name, location_type, category, address, website, latitude, longitude, opening_hours, description, maps_url)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                int(row["id"]),
                row["name"],
                row["location_type"],
                row["category"],
                row["address"],
                row["website"],
                latitude,
                longitude,
                row["opening_hours"],
                row["description"],
                row["maps_url"]
            ))

    conn.commit()
    conn.close()


def add_user(first_name, last_name, birthdate, nova_mail, password):
    nova_mail = nova_mail.lower().strip()
    conn = connect_db()
    cursor = conn.cursor()
    try:
        cursor.execute("""
            INSERT INTO users
            (username, first_name, last_name, birthdate, nova_mail, password)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (nova_mail, first_name, last_name, str(birthdate), nova_mail, hash_password(password)))
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        return False
    finally:
        conn.close()


def login_user(nova_mail, password):
    nova_mail = nova_mail.lower().strip()
    conn = connect_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE username = ? AND password = ?", (nova_mail, hash_password(password)))
    user = cursor.fetchone()
    conn.close()
    return user


def get_user(username):
    conn = connect_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE username = ?", (username,))
    user = cursor.fetchone()
    conn.close()
    return user


def format_user(username):
    user = get_user(username)
    if user is None:
        return username
    return f"{user[4]} ({user[1]} {user[2]})"


def get_all_users_except(username):
    conn = connect_db()
    cursor = conn.cursor()
    cursor.execute("SELECT username, first_name, last_name, nova_mail FROM users WHERE username != ? ORDER BY first_name", (username,))
    users = cursor.fetchall()
    conn.close()
    return users


def search_users(query):
    conn = connect_db()
    cursor = conn.cursor()
    q = f"%{query.lower().strip()}%"
    cursor.execute("""
        SELECT username, first_name, last_name, nova_mail
        FROM users
        WHERE lower(first_name) LIKE ? OR lower(last_name) LIKE ? OR lower(nova_mail) LIKE ?
        ORDER BY first_name
    """, (q, q, q))
    users = cursor.fetchall()
    conn.close()
    return users


def follow_user(follower, followed):
    conn = connect_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM follows WHERE follower_username = ? AND followed_username = ?", (follower, followed))
    if cursor.fetchone() is None and follower != followed:
        cursor.execute("INSERT INTO follows (follower_username, followed_username) VALUES (?, ?)", (follower, followed))
    conn.commit()
    conn.close()


def unfollow_user(follower, followed):
    conn = connect_db()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM follows WHERE follower_username = ? AND followed_username = ?", (follower, followed))
    conn.commit()
    conn.close()


def remove_follower(current_user, follower):
    unfollow_user(follower, current_user)


def get_followers(username):
    conn = connect_db()
    cursor = conn.cursor()
    cursor.execute("SELECT follower_username FROM follows WHERE followed_username = ?", (username,))
    followers = cursor.fetchall()
    conn.close()
    return [f[0] for f in followers]


def get_following(username):
    conn = connect_db()
    cursor = conn.cursor()
    cursor.execute("SELECT followed_username FROM follows WHERE follower_username = ?", (username,))
    following = cursor.fetchall()
    conn.close()
    return [f[0] for f in following]


def post_item(title, description, category, price, seller_username, post_type, image_path, end_time=None):
    conn = connect_db()
    cursor = conn.cursor()
    created_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    cursor.execute("""
        INSERT INTO items
        (title, description, category, price, seller_username, post_type, created_at, image_path, status, end_time)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'available', ?)
    """, (title, description, category, price, seller_username, post_type, created_at, image_path, end_time))
    conn.commit()
    conn.close()


def get_item_end_time(item_id):
    conn = connect_db()
    cursor = conn.cursor()
    cursor.execute("SELECT end_time FROM items WHERE id = ?", (item_id,))
    row = cursor.fetchone()
    conn.close()
    return row[0] if row else None


def auto_close_expired_auctions():
    conn = connect_db()
    cursor = conn.cursor()
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    cursor.execute("""
        UPDATE items
        SET status = 'unavailable'
        WHERE post_type = 'auction'
          AND status = 'available'
          AND end_time IS NOT NULL
          AND end_time < ?
    """, (now,))
    conn.commit()
    conn.close()


def get_highest_bid(item_id):
    conn = connect_db()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT amount, bidder_username
        FROM bids
        WHERE item_id = ?
        ORDER BY amount DESC, created_at DESC
        LIMIT 1
    """, (item_id,))
    row = cursor.fetchone()
    conn.close()
    return row


def get_bid_count(item_id):
    conn = connect_db()
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM bids WHERE item_id = ?", (item_id,))
    count = cursor.fetchone()[0]
    conn.close()
    return count


def place_bid(item_id, bidder, amount, starting_price):
    conn = connect_db()
    cursor = conn.cursor()
    cursor.execute("SELECT MAX(amount) FROM bids WHERE item_id = ?", (item_id,))
    current_max = cursor.fetchone()[0]
    floor = current_max if current_max is not None else starting_price
    if amount <= floor:
        conn.close()
        return False
    created_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    cursor.execute("""
        INSERT INTO bids (item_id, bidder_username, amount, created_at)
        VALUES (?, ?, ?, ?)
    """, (item_id, bidder, amount, created_at))
    conn.commit()
    conn.close()
    return True


def search_items(query="", category="All"):
    conn = connect_db()
    cursor = conn.cursor()
    q = f"%{query.lower().strip()}%"

    if category == "All":
        cursor.execute("""
            SELECT id, title, description, category, price, seller_username, post_type, created_at, image_path, status
            FROM items
            WHERE status = 'available'
              AND (lower(title) LIKE ? OR lower(description) LIKE ? OR lower(category) LIKE ? OR lower(post_type) LIKE ?)
            ORDER BY created_at DESC
        """, (q, q, q, q))
    else:
        cursor.execute("""
            SELECT id, title, description, category, price, seller_username, post_type, created_at, image_path, status
            FROM items
            WHERE status = 'available'
              AND category = ?
              AND (lower(title) LIKE ? OR lower(description) LIKE ? OR lower(category) LIKE ? OR lower(post_type) LIKE ?)
            ORDER BY created_at DESC
        """, (category, q, q, q, q))

    items = cursor.fetchall()
    conn.close()
    return items


def get_favorite_count(item_id):
    conn = connect_db()
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM favorites WHERE item_id = ?", (item_id,))
    count = cursor.fetchone()[0]
    conn.close()
    return count


def get_items_by_user(username):
    conn = connect_db()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT id, title, description, category, price, seller_username, post_type, created_at, image_path, status
        FROM items
        WHERE seller_username = ?
        ORDER BY created_at DESC
    """, (username,))
    items = cursor.fetchall()
    conn.close()
    return items


def get_old_active_items_by_user(username, minimum_days=60):
    conn = connect_db()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT id, title, description, category, price, seller_username, post_type, created_at, image_path, status,
               CAST(julianday('now') - julianday(created_at) AS INTEGER) AS days_online
        FROM items
        WHERE seller_username = ?
          AND status = 'available'
          AND post_type IN ('sell', 'auction', 'gift')
          AND CAST(julianday('now') - julianday(created_at) AS INTEGER) >= ?
        ORDER BY created_at ASC
    """, (username, minimum_days))
    items = cursor.fetchall()
    conn.close()
    return items


def delete_item(item_id, current_user):
    conn = connect_db()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM favorites WHERE item_id = ?", (item_id,))
    cursor.execute("DELETE FROM items WHERE id = ? AND seller_username = ?", (item_id, current_user))
    changed = cursor.rowcount
    conn.commit()
    conn.close()
    return changed > 0


def find_conversation(item_id, buyer, seller):
    conn = connect_db()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT id, item_id, buyer_username, seller_username, created_at
        FROM conversations
        WHERE item_id = ? AND buyer_username = ? AND seller_username = ?
    """, (item_id, buyer, seller))
    row = cursor.fetchone()
    conn.close()
    return row


def get_or_create_conversation(item_id, buyer, seller):
    if buyer == seller:
        return None
    existing = find_conversation(item_id, buyer, seller)
    if existing is not None:
        return existing[0]
    conn = connect_db()
    cursor = conn.cursor()
    created_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    cursor.execute("""
        INSERT INTO conversations (item_id, buyer_username, seller_username, created_at)
        VALUES (?, ?, ?, ?)
    """, (item_id, buyer, seller, created_at))
    new_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return new_id


def send_message(conv_id, sender, body):
    cleaned = body.strip()
    if cleaned == "":
        return False
    conn = connect_db()
    cursor = conn.cursor()
    sent_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    cursor.execute("""
        INSERT INTO messages (conversation_id, sender_username, body, sent_at, read_at)
        VALUES (?, ?, ?, ?, NULL)
    """, (conv_id, sender, cleaned, sent_at))
    conn.commit()
    conn.close()
    return True


def get_conversations_for_user(username):
    conn = connect_db()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT id, item_id, buyer_username, seller_username, created_at
        FROM conversations
        WHERE buyer_username = ? OR seller_username = ?
    """, (username, username))
    rows = cursor.fetchall()
    conn.close()
    return rows


def get_latest_message(conv_id):
    conn = connect_db()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT id, conversation_id, sender_username, body, sent_at, read_at
        FROM messages
        WHERE conversation_id = ?
        ORDER BY sent_at DESC, id DESC
        LIMIT 1
    """, (conv_id,))
    row = cursor.fetchone()
    conn.close()
    return row


def count_unread_in_conversation(conv_id, current_user):
    conn = connect_db()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT COUNT(*) FROM messages
        WHERE conversation_id = ?
          AND sender_username != ?
          AND read_at IS NULL
    """, (conv_id, current_user))
    count = cursor.fetchone()[0]
    conn.close()
    return count


def count_unread_threads(username):
    total = 0
    for conv in get_conversations_for_user(username):
        if count_unread_in_conversation(conv[0], username) > 0:
            total += 1
    return total


def get_thread_messages(conv_id, limit):
    conn = connect_db()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT id, conversation_id, sender_username, body, sent_at, read_at
        FROM messages
        WHERE conversation_id = ?
        ORDER BY sent_at ASC, id ASC
        LIMIT ?
    """, (conv_id, limit))
    rows = cursor.fetchall()
    conn.close()
    return rows


def mark_thread_read(conv_id, current_user):
    conn = connect_db()
    cursor = conn.cursor()
    read_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    cursor.execute("""
        UPDATE messages
        SET read_at = ?
        WHERE conversation_id = ?
          AND sender_username != ?
          AND read_at IS NULL
    """, (read_at, conv_id, current_user))
    conn.commit()
    conn.close()


def get_item_or_none(item_id):
    conn = connect_db()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT id, title, description, category, price, seller_username, post_type, created_at, image_path, status
        FROM items
        WHERE id = ?
    """, (item_id,))
    row = cursor.fetchone()
    conn.close()
    return row


def ensure_demo_warning_post():
    demo_user = "10000@novasbe.pt"
    user = get_user(demo_user)
    if user is None:
        return

    old_items = get_old_active_items_by_user(demo_user, minimum_days=60)
    if len(old_items) > 0:
        return

    conn = connect_db()
    cursor = conn.cursor()
    created_at = (datetime.now() - timedelta(days=66)).strftime("%Y-%m-%d %H:%M:%S")
    cursor.execute("""
        INSERT INTO items
        (title, description, category, price, seller_username, post_type, created_at, image_path, status)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'available')
    """, (
        "Old demo jacket",
        "Demo post for the login reminder. This item has been online for more than two months.",
        "clothes",
        15,
        demo_user,
        "sell",
        created_at,
        "uploaded_images/clothes_1.png"
    ))
    conn.commit()
    conn.close()


def favorite_item(username, item_id):
    conn = connect_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM favorites WHERE username = ? AND item_id = ?", (username, item_id))
    if cursor.fetchone() is None:
        cursor.execute("INSERT INTO favorites (username, item_id) VALUES (?, ?)", (username, item_id))
    conn.commit()
    conn.close()


def remove_favorite(username, item_id):
    conn = connect_db()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM favorites WHERE username = ? AND item_id = ?", (username, item_id))
    conn.commit()
    conn.close()


def get_favorite_items(username):
    conn = connect_db()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT items.id, items.title, items.description, items.category, items.price,
               items.seller_username, items.post_type, items.created_at, items.image_path, items.status
        FROM favorites
        JOIN items ON favorites.item_id = items.id
        WHERE favorites.username = ?
        ORDER BY items.created_at DESC
    """, (username,))
    items = cursor.fetchall()
    conn.close()
    return items


def set_item_status(item_id, new_status, current_user):
    conn = connect_db()
    cursor = conn.cursor()
    cursor.execute("""
        UPDATE items
        SET status = ?
        WHERE id = ? AND seller_username = ?
    """, (new_status, item_id, current_user))
    changed = cursor.rowcount
    conn.commit()
    conn.close()
    return changed > 0



def get_disposal_categories():
    conn = connect_db()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT DISTINCT category
        FROM disposal_locations
        ORDER BY category
    """)
    categories = [row[0] for row in cursor.fetchall()]
    conn.close()
    return categories


def get_disposal_locations(category="All", query=""):
    conn = connect_db()
    cursor = conn.cursor()
    q = f"%{query.lower().strip()}%"

    if category == "All":
        cursor.execute("""
            SELECT id, name, location_type, category, address, website,
                   latitude, longitude, opening_hours, description, maps_url
            FROM disposal_locations
            WHERE lower(name) LIKE ?
               OR lower(location_type) LIKE ?
               OR lower(category) LIKE ?
               OR lower(address) LIKE ?
               OR lower(description) LIKE ?
            ORDER BY category, name
        """, (q, q, q, q, q))
    else:
        cursor.execute("""
            SELECT id, name, location_type, category, address, website,
                   latitude, longitude, opening_hours, description, maps_url
            FROM disposal_locations
            WHERE category = ?
              AND (lower(name) LIKE ?
               OR lower(location_type) LIKE ?
               OR lower(category) LIKE ?
               OR lower(address) LIKE ?
               OR lower(description) LIKE ?)
            ORDER BY name
        """, (category, q, q, q, q, q))

    locations = cursor.fetchall()
    conn.close()
    return locations


def locations_to_map_df(locations, user_lat=None, user_lon=None):
    rows = []
    for loc in locations:
        loc_id, name, location_type, category, address, website, latitude, longitude, opening_hours, description, maps_url = loc
        if latitude is not None and longitude is not None:
            rows.append({
                "name": name,
                "latitude": latitude,
                "longitude": longitude,
                "category": category,
                "type": location_type,
                "address": address,
                "opening_hours": opening_hours,
                "maps_url": maps_url,
                "point_type": "Disposal location",
            })

    if user_lat is not None and user_lon is not None:
        rows.append({
            "name": "Your entered address",
            "latitude": user_lat,
            "longitude": user_lon,
            "category": "user",
            "type": "Your location",
            "address": "User address",
            "opening_hours": "",
            "maps_url": "",
            "point_type": "User",
        })

    return pd.DataFrame(rows)


def geocode_demo_address(address):
    cleaned = address.lower().strip()

    known_addresses = {
        "nova sbe": (38.6781, -9.3273),
        "nova school of business": (38.6781, -9.3273),
        "carcavelos": (38.6781, -9.3273),
        "marquês de pombal": (38.7253, -9.1500),
        "marques de pombal": (38.7253, -9.1500),
        "saldanha": (38.7350, -9.1450),
        "campo pequeno": (38.7425, -9.1450),
        "largo da graça": (38.7162, -9.1306),
        "largo da graca": (38.7162, -9.1306),
        "almirante reis": (38.7285, -9.1355),
        "alcântara": (38.7040, -9.1780),
        "alcantara": (38.7040, -9.1780),
        "algés": (38.7062, -9.2263),
        "alges": (38.7062, -9.2263),
        "almada": (38.6794, -9.1581),
        "amadora": (38.7598, -9.2303),
        "oeiras": (38.7157, -9.3055),
    }

    for key, coords in known_addresses.items():
        if key in cleaned:
            return coords, "Matched a known demo area."

    # Try to match one of the disposal addresses already stored in the database.
    conn = connect_db()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT address, latitude, longitude
        FROM disposal_locations
        WHERE latitude IS NOT NULL AND longitude IS NOT NULL
    """)
    disposal_addresses = cursor.fetchall()
    conn.close()

    for stored_address, latitude, longitude in disposal_addresses:
        stored_cleaned = stored_address.lower()
        if cleaned != "" and (cleaned in stored_cleaned or stored_cleaned in cleaned):
            return (latitude, longitude), "Matched a stored disposal address."

    if cleaned == "":
        return None, "Enter an address first."

    if "lisboa" in cleaned or "lisbon" in cleaned:
        return (38.7223, -9.1393), "Approximation: central Lisbon."

    return (38.7223, -9.1393), "Approximation: central Lisbon. Add this address to the demo geocoder for more precision."


def show_location_map(map_df):
    if len(map_df) == 0:
        st.info("No map data available.")
        return

    center_lat = map_df["latitude"].mean()
    center_lon = map_df["longitude"].mean()

    layer = pdk.Layer(
        "ScatterplotLayer",
        data=map_df,
        get_position="[longitude, latitude]",
        get_radius=85,
        pickable=True,
        opacity=0.8,
        stroked=True,
        filled=True,
        get_fill_color="[30, 120, 180, 180]",
        get_line_color="[255, 255, 255]",
    )

    view_state = pdk.ViewState(
        latitude=center_lat,
        longitude=center_lon,
        zoom=11,
        pitch=0,
    )

    tooltip = {
        "html": "<b>{name}</b><br/>{type}<br/>{address}<br/>Opening hours: {opening_hours}",
        "style": {"backgroundColor": "white", "color": "black"},
    }

    st.pydeck_chart(pdk.Deck(layers=[layer], initial_view_state=view_state, tooltip=tooltip))

def save_uploaded_image(uploaded_file):
    if uploaded_file is None:
        return None
    file_name = datetime.now().strftime("%Y%m%d%H%M%S") + "_" + uploaded_file.name
    image_path = os.path.join(IMAGE_FOLDER, file_name)
    with open(image_path, "wb") as file:
        file.write(uploaded_file.getbuffer())
    return image_path


def resolve_image_path(image_path):
    if image_path is None or image_path == "":
        return None
    if os.path.isabs(image_path):
        return image_path
    return os.path.join(BASE_DIR, image_path)


def find_item_photo(item_id):
    for ext in ("jpg", "jpeg", "png", "webp"):
        candidate = os.path.join(ITEM_PHOTOS_FOLDER, f"{item_id}.{ext}")
        if os.path.exists(candidate):
            return candidate
    return None


def resolve_item_image(item_id, fallback_image_path):
    photo = find_item_photo(item_id)
    if photo is not None:
        return photo
    return resolve_image_path(fallback_image_path)


def display_item(
    item,
    current_user=None,
    allow_favorite=True,
    allow_remove_favorite=False,
    owner_controls=False,
    show_contact_button=False,
    key_prefix="item"
):
    item_id, title, description, category, price, seller_username, post_type, created_at, image_path, status = item[:10]
    likes = get_favorite_count(item_id)
    unavailable = status != "available"

    if unavailable:
        st.markdown("---")
        st.caption("Unavailable item")

    st.subheader(title)

    full_image_path = resolve_item_image(item_id, image_path)
    if full_image_path is not None and os.path.exists(full_image_path):
        st.image(full_image_path, width=260)

    st.write(f"Description: {description}")
    st.write(f"Category: {category}")
    st.write(f"Type: {post_type}")
    st.write(f"Seller: {format_user(seller_username)}")
    st.write(f"Posted on: {created_at}")
    st.write(f"Status: {status}")
    st.write(f"Likes: {likes}")

    if post_type == "sell":
        st.write(f"Price: {price}€")
    elif post_type == "auction":
        highest_bid = get_highest_bid(item_id)
        bid_count = get_bid_count(item_id)
        if highest_bid is None:
            st.write(f"Starting price: {price}€  ·  No bids yet")
            next_min_bid = price + 1
        else:
            st.write(f"Current bid: {highest_bid[0]}€  ·  {bid_count} bid{'s' if bid_count != 1 else ''}")
            next_min_bid = highest_bid[0] + 1

        end_time_str = get_item_end_time(item_id)
        auction_active = False
        if end_time_str is not None:
            end_dt = datetime.strptime(end_time_str, "%Y-%m-%d %H:%M:%S")
            start_dt = datetime.strptime(created_at, "%Y-%m-%d %H:%M:%S")
            now = datetime.now()
            if end_dt > now:
                auction_active = True
                total_seconds = (end_dt - start_dt).total_seconds()
                elapsed_seconds = (now - start_dt).total_seconds()
                progress_value = max(0.0, min(elapsed_seconds / total_seconds, 1.0)) if total_seconds > 0 else 1.0
                st.progress(progress_value)
                remaining = end_dt - now
                days = remaining.days
                hours = remaining.seconds // 3600
                minutes = (remaining.seconds % 3600) // 60
                if days > 0:
                    st.caption(f"Ends in {days}d {hours}h {minutes}m")
                elif hours > 0:
                    st.caption(f"Ends in {hours}h {minutes}m")
                else:
                    st.caption(f"Ends in {minutes}m")
            else:
                st.progress(1.0)
                if highest_bid is None:
                    st.caption("Auction ended. No bids.")
                else:
                    st.caption(f"Auction ended. Winner: {format_user(highest_bid[1])} at {highest_bid[0]}€")

        if (current_user is not None
                and current_user != seller_username
                and status == "available"
                and auction_active):
            bid_input = st.number_input(
                "Your bid (€)",
                min_value=next_min_bid,
                value=next_min_bid,
                key=f"{key_prefix}_bid_amount_{item_id}",
            )
            if st.button("Place bid", key=f"{key_prefix}_bid_btn_{item_id}"):
                if place_bid(item_id, current_user, bid_input, price):
                    st.success(f"Bid of {bid_input}€ placed.")
                    st.rerun()
                else:
                    st.error("Bid rejected. Someone outbid you — try a higher amount.")
    elif post_type == "searching":
        st.write(f"Maximum amount willing to pay: {price}€")
    else:
        st.write("Price: free")

    if unavailable:
        st.info("This post is unavailable. Actions are disabled.")

    if current_user is not None and seller_username == current_user and owner_controls:
        st.write("Owner controls")
        col1, col2 = st.columns(2)
        if status == "available":
            if col1.button("Mark unavailable", key=f"{key_prefix}_owner_unavailable_{item_id}"):
                set_item_status(item_id, "unavailable", current_user)
                st.success("Item marked as unavailable.")
                st.rerun()
        else:
            if col1.button("Mark available", key=f"{key_prefix}_owner_available_{item_id}"):
                set_item_status(item_id, "available", current_user)
                st.success("Item marked as available.")
                st.rerun()

        if col2.button("Delete post", key=f"{key_prefix}_owner_delete_{item_id}"):
            delete_item(item_id, current_user)
            st.success("Post deleted.")
            st.rerun()

    if current_user is not None and seller_username != current_user and not unavailable:
        if allow_favorite:
            if st.button(f"Add to favorites", key=f"{key_prefix}_fav_{item_id}"):
                favorite_item(current_user, item_id)
                st.success("Added to favorites.")
                st.rerun()

        if show_contact_button:
            existing_conv = find_conversation(item_id, current_user, seller_username)
            if existing_conv is None:
                composer_body = st.text_area(
                    "Message the seller",
                    key=f"{key_prefix}_compose_{item_id}",
                    placeholder="Hi, is this still available?",
                )
                if st.button("Send", key=f"{key_prefix}_send_{item_id}"):
                    new_conv_id = get_or_create_conversation(item_id, current_user, seller_username)
                    if new_conv_id is None:
                        st.error("You cannot message yourself about your own item.")
                    elif send_message(new_conv_id, current_user, composer_body):
                        st.success("Message sent.")
                        st.rerun()
                    else:
                        st.error("Type a message before sending.")
            else:
                st.info("You have an open conversation about this item.")
                if st.button("Open in Messages", key=f"{key_prefix}_open_{item_id}"):
                    st.session_state.active_page = "Messages"
                    st.session_state.active_thread = existing_conv[0]
                    st.rerun()

        if post_type == "searching":
            st.info("This user is searching for this item.")

    if current_user is not None and allow_remove_favorite:
        if st.button("Unfavorite", key=f"{key_prefix}_remove_fav_{item_id}"):
            remove_favorite(current_user, item_id)
            st.success("Removed from favorites.")
            st.rerun()

    st.divider()



@st.dialog("Recycling reminder")
def old_post_warning_dialog(old_items):
    st.write("Some of your active posts have been online for more than two months.")
    st.write("It may be time to recycle, donate, or delete them.")

    for warning_item in old_items[:5]:
        st.write(f"- {warning_item[1]} ({warning_item[10]} days online)")

    if st.button("Close window", key="modal_close_old_post_warning"):
        st.session_state.show_old_post_warning = False
        st.rerun()


create_tables()
import_demo_data()
import_disposal_data()
ensure_demo_warning_post()
auto_close_expired_auctions()

if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
if "username" not in st.session_state:
    st.session_state.username = None
if "active_page" not in st.session_state:
    st.session_state.active_page = "Marketplace"
if "show_old_post_warning" not in st.session_state:
    st.session_state.show_old_post_warning = False
if "active_thread" not in st.session_state:
    st.session_state.active_thread = None

st.markdown(
    """
    <style>
      [data-testid="stSidebar"] { background-color: #ffd9df; }
      .stButton button {
          border-radius: 14px;
          border: 1px solid #ff1236;
      }
      div[data-testid="stContainer"] { border-radius: 18px; }
      h1, h2, h3 { color: #111; }
    </style>
    <div style="display:flex; align-items:center; gap:18px; margin-bottom:8px;">
      <div style="width:64px; height:64px; border-radius:16px;
                  background:linear-gradient(135deg,#ff1236,#ff3655);
                  display:flex; align-items:center; justify-content:center;
                  box-shadow:0 6px 16px rgba(255,18,54,0.28);">
        <div style="width:34px; height:34px; border:4px solid white;
                    border-radius:50%; position:relative;">
          <div style="position:absolute; width:54px; height:14px;
                      border:4px solid white; border-radius:50%;
                      transform:rotate(-18deg); top:7px; left:-14px;"></div>
          <div style="width:7px; height:7px; background:white;
                      border-radius:50%; position:absolute; top:3px; right:-3px;"></div>
        </div>
      </div>
      <div>
        <div style="font-size:38px; font-weight:900; letter-spacing:1px; line-height:0.9;">NOVA</div>
        <div style="font-size:14px; letter-spacing:6px; color:#ff2347; margin-top:4px;">MARKETPLACE</div>
      </div>
    </div>
    <div style="font-size:15px; margin-bottom:24px;">
      Buy<span style="color:#ff2347;font-weight:bold;">.</span>
      Sell<span style="color:#ff2347;font-weight:bold;">.</span>
      Gift<span style="color:#ff2347;font-weight:bold;">.</span>
      Nova<span style="color:#ff2347;font-weight:bold;">.</span>
    </div>
    """,
    unsafe_allow_html=True,
)

if not st.session_state.logged_in:
    st.sidebar.write("Menu")
    if st.sidebar.button("Create Profile", use_container_width=True):
        st.session_state.active_page = "Create Profile"
    if st.sidebar.button("Login", use_container_width=True):
        st.session_state.active_page = "Login"

    if st.session_state.active_page not in ["Create Profile", "Login"]:
        st.session_state.active_page = "Login"

    if st.session_state.active_page == "Create Profile":
        st.header("Create Profile")
        first_name = st.text_input("Name")
        last_name = st.text_input("Last name")
        birthdate = st.date_input("Birthday", min_value=datetime(1950, 1, 1).date(), max_value=datetime.today().date())
        nova_mail = st.text_input("Nova mail", placeholder="12345@novasbe.pt").lower().strip()
        password = st.text_input("Password", type="password")
        if nova_mail != "":
            st.info(f"Your username will be: {nova_mail}")
        if st.button("Create Profile"):
            if first_name == "" or last_name == "" or nova_mail == "" or password == "":
                st.error("Please fill in all fields.")
            elif len(nova_mail) != 16 or not nova_mail[:5].isdigit() or nova_mail[5:] != "@novasbe.pt":
                st.error("Nova mail must be 5 numbers followed by @novasbe.pt, for example 12345@novasbe.pt.")
            else:
                success = add_user(first_name, last_name, birthdate, nova_mail, password)
                if success:
                    st.success("Profile created successfully. You can now log in.")
                else:
                    st.error("This Nova mail already exists.")

    elif st.session_state.active_page == "Login":
        st.header("Login")
        nova_mail = st.text_input("Nova mail").lower().strip()
        password = st.text_input("Password", type="password")
        if st.button("Login"):
            user = login_user(nova_mail, password)
            if user:
                st.session_state.logged_in = True
                st.session_state.username = nova_mail
                st.session_state.active_page = "Marketplace"
                st.session_state.show_old_post_warning = True
                st.success("Logged in successfully.")
                st.rerun()
            else:
                st.error("Wrong Nova mail or password.")

else:
    current_user = st.session_state.username
    st.sidebar.write("Logged in as:")
    st.sidebar.write(f"**{current_user}**")
    if st.sidebar.button("Logout", use_container_width=True):
        st.session_state.logged_in = False
        st.session_state.username = None
        st.session_state.show_old_post_warning = False
        st.session_state.active_thread = None
        st.rerun()

    st.sidebar.divider()
    st.sidebar.write("Menu")
    if st.sidebar.button("My Area", use_container_width=True):
        st.session_state.active_page = "My Area"

    unread_count = count_unread_threads(current_user)
    messages_label = f"Messages ({unread_count})" if unread_count > 0 else "Messages"
    if st.sidebar.button(messages_label, use_container_width=True):
        st.session_state.active_page = "Messages"

    for page in ["Marketplace", "New post", "Disposal Locations"]:
        if st.sidebar.button(page, use_container_width=True):
            st.session_state.active_page = page

    menu = st.session_state.active_page

    old_items_for_warning = get_old_active_items_by_user(current_user, minimum_days=60)
    if st.session_state.show_old_post_warning and len(old_items_for_warning) > 0:
        # Show once per login. Closing the popup does not snooze or edit the product.
        st.session_state.show_old_post_warning = False
        old_post_warning_dialog(old_items_for_warning)

    if menu == "My Area":
        st.header("My Area")
        user = get_user(current_user)
        followers = get_followers(current_user)
        following = get_following(current_user)
        recommendations = get_all_users_except(current_user)

        st.subheader("Profile details")
        st.write(f"Name: {user[1]}")
        st.write(f"Last name: {user[2]}")
        st.write(f"Birthday: {user[3]}")
        st.write(f"Nova mail / Username: {user[4]}")

        with st.expander(f"Followers ({len(followers)})", expanded=False):
            follower_search = st.text_input("Search followers", key="search_followers").lower().strip()
            filtered_followers = [f for f in followers if follower_search in format_user(f).lower()]

            if len(filtered_followers) == 0:
                st.info("No matching followers.")
            else:
                for follower in filtered_followers:
                    col1, col2 = st.columns([3, 1])
                    col1.write(format_user(follower))
                    if col2.button("Remove", key=f"remove_follower_{follower}"):
                        remove_follower(current_user, follower)
                        st.success("Follower removed.")
                        st.rerun()

        with st.expander(f"Following ({len(following)})", expanded=False):
            following_search = st.text_input("Search following", key="search_following").lower().strip()
            filtered_following = [f for f in following if following_search in format_user(f).lower()]

            if len(filtered_following) == 0:
                st.info("No matching following users.")
            else:
                for followed in filtered_following:
                    col1, col2 = st.columns([3, 1])
                    col1.write(format_user(followed))
                    if col2.button("Unfollow", key=f"unfollow_{followed}"):
                        unfollow_user(current_user, followed)
                        st.success("User unfollowed.")
                        st.rerun()

        with st.expander("People you could follow", expanded=False):
            recommendation_search = st.text_input("Search recommendations", key="search_recommendations").lower().strip()
            visible_recommendations = []
            for rec in recommendations:
                rec_username, rec_name, rec_last_name, rec_mail = rec
                label = f"{rec_mail} ({rec_name} {rec_last_name})"
                if rec_username not in following and recommendation_search in label.lower():
                    visible_recommendations.append(rec)

            if len(visible_recommendations) == 0:
                st.info("No recommendations found.")
            else:
                for rec in visible_recommendations[:30]:
                    rec_username, rec_name, rec_last_name, rec_mail = rec
                    col1, col2 = st.columns([3, 1])
                    col1.write(f"{rec_mail} ({rec_name} {rec_last_name})")
                    if col2.button("Follow", key=f"follow_{rec_username}"):
                        follow_user(current_user, rec_username)
                        st.success("User followed.")
                        st.rerun()

        with st.expander("My posted items", expanded=False):
            my_items = get_items_by_user(current_user)
            if len(my_items) == 0:
                st.info("You have not posted any items yet.")
            else:
                items_per_row = 2
                for row_start in range(0, len(my_items), items_per_row):
                    cols = st.columns(items_per_row)
                    for offset, col in enumerate(cols):
                        index = row_start + offset
                        if index < len(my_items):
                            with col:
                                with st.container(border=True):
                                    display_item(
                                        my_items[index],
                                        current_user=current_user,
                                        allow_favorite=False,
                                        owner_controls=True,
                                        key_prefix=f"my_posts_{index}",
                                    )

        with st.expander("My favorite items", expanded=False):
            favorites = get_favorite_items(current_user)
            if len(favorites) == 0:
                st.info("You have no favorite items yet.")
            else:
                items_per_row = 2
                for row_start in range(0, len(favorites), items_per_row):
                    cols = st.columns(items_per_row)
                    for offset, col in enumerate(cols):
                        index = row_start + offset
                        if index < len(favorites):
                            with col:
                                with st.container(border=True):
                                    display_item(
                                        favorites[index],
                                        current_user=current_user,
                                        allow_favorite=False,
                                        allow_remove_favorite=True,
                                        owner_controls=False,
                                        show_contact_button=True,
                                        key_prefix=f"favorites_{index}",
                                    )

    elif menu == "New post":
        st.header("New post")
        st.info("Use this page to create a new post. Browse other people's posts on the Marketplace page.")

        if st.session_state.get("post_just_created"):
            st.balloons()
            st.success("Post created successfully!")
            st.session_state.post_just_created = False

        marketplace_option = st.selectbox(
            "Choose post type",
            ["Sell", "Auction", "Gift", "Searching"],
            key="new_post_type",
        )

        st.subheader(marketplace_option)
        title = st.text_input("Item title", key="new_post_title")
        description = st.text_area("Description", key="new_post_description")
        category = st.selectbox("Category", CATEGORIES, key="new_post_category")
        post_type = marketplace_option.lower()

        end_time_value = None

        if post_type == "gift":
            price = 0
            st.info("Gifting items are free, so no price is needed.")
        elif post_type == "searching":
            price = st.number_input("Maximum amount you would pay", min_value=0, value=0, key="new_post_price")
        elif post_type == "auction":
            price = st.number_input("Starting price", min_value=0, value=0, key="new_post_price")
            auction_end_date = st.date_input(
                "Auction end date",
                value=datetime.now().date() + timedelta(days=7),
                min_value=datetime.now().date() + timedelta(days=1),
                key="new_post_end_date",
            )
            end_time_value = auction_end_date.strftime("%Y-%m-%d") + " 23:59:59"
        else:
            price = st.number_input("Price", min_value=0, value=0, key="new_post_price")

        uploaded_image = st.file_uploader(
            "Upload item image",
            type=["png", "jpg", "jpeg"],
            key="new_post_image",
        )

        if st.button("Post"):
            if title == "":
                st.error("Please enter an item title.")
            else:
                image_path = save_uploaded_image(uploaded_image)
                post_item(title, description, category, price, current_user, post_type, image_path, end_time_value)
                for k in ("new_post_title", "new_post_description", "new_post_price", "new_post_image", "new_post_end_date"):
                    if k in st.session_state:
                        del st.session_state[k]
                st.session_state.post_just_created = True
                st.rerun()

    elif menu == "Disposal Locations":
        st.header("Disposal Locations")
        st.write("Find places in Lisbon and surroundings where items can be donated, reused, or disposed of responsibly.")
        st.write("Use the map or list below. To get directions, open the Google Maps link and enter your address there.")

        disposal_categories = ["All"] + get_disposal_categories()
        category_filter = st.selectbox("Filter by category", disposal_categories, key="disposal_category")
        disposal_query = st.text_input("Search by name, type, address, or description", key="disposal_search")

        locations = get_disposal_locations(category_filter, disposal_query)
        st.subheader(f"Locations ({len(locations)})")

        map_df = locations_to_map_df(locations)
        show_location_map(map_df)

        with st.expander("Show location list", expanded=True):
            if len(locations) == 0:
                st.info("No disposal locations found.")
            else:
                for loc in locations:
                    loc_id, name, location_type, category, address, website, latitude, longitude, opening_hours, description, maps_url = loc
                    with st.container(border=True):
                        st.subheader(name)
                        st.write(f"Category: {category}")
                        st.write(f"Type: {location_type}")
                        if address != "":
                            st.write(f"Address: {address}")
                        st.write(f"Opening hours: {opening_hours if opening_hours != '' else 'Unknown'}")
                        if description != "":
                            st.write(description)
                        if maps_url != "":
                            st.link_button("Open in Google Maps", maps_url, key=f"maps_{loc_id}")
                        elif website != "":
                            st.link_button("Open website", website, key=f"website_{loc_id}")

    elif menu == "Marketplace":
        st.header("Marketplace")

        tab_products, tab_newest = st.tabs(["Product search", "Newest uploads"])

        with tab_products:
            product_query = st.text_input("Search product", key="product_search")
            product_category = st.selectbox("Filter by category", ["All"] + CATEGORIES, key="product_category_filter")

            product_results = search_items(product_query, product_category)
            st.subheader(f"Product results ({len(product_results)})")

            if len(product_results) == 0:
                st.info("No products found.")
            else:
                items_per_row = 2
                for row_start in range(0, len(product_results), items_per_row):
                    cols = st.columns(items_per_row)
                    for offset, col in enumerate(cols):
                        index = row_start + offset
                        if index < len(product_results):
                            with col:
                                with st.container(border=True):
                                    display_item(
                                        product_results[index],
                                        current_user=current_user,
                                        show_contact_button=True,
                                        key_prefix=f"product_search_{index}",
                                    )

        with tab_newest:
            newest_category = st.selectbox("Filter newest uploads by category", ["All"] + CATEGORIES, key="newest_category_filter")
            newest_items = search_items("", newest_category)[:30]
            st.subheader(f"Newest uploads ({len(newest_items)})")

            if len(newest_items) == 0:
                st.info("No uploads found.")
            else:
                items_per_row = 2
                for row_start in range(0, len(newest_items), items_per_row):
                    cols = st.columns(items_per_row)
                    for offset, col in enumerate(cols):
                        index = row_start + offset
                        if index < len(newest_items):
                            with col:
                                with st.container(border=True):
                                    display_item(
                                        newest_items[index],
                                        current_user=current_user,
                                        show_contact_button=True,
                                        key_prefix=f"newest_{index}",
                                    )

    elif menu == "Messages":
        st.header("Messages")

        if st.session_state.active_thread is None:
            conversations = get_conversations_for_user(current_user)

            inbox_rows = []
            for conv in conversations:
                conv_id, conv_item_id, buyer, seller, conv_created_at = conv
                latest = get_latest_message(conv_id)
                if latest is None:
                    continue
                unread = count_unread_in_conversation(conv_id, current_user)
                item_row = get_item_or_none(conv_item_id)
                other_party = seller if current_user == buyer else buyer
                inbox_rows.append({
                    "conv_id": conv_id,
                    "item_row": item_row,
                    "other_party": other_party,
                    "latest": latest,
                    "unread": unread,
                })

            inbox_rows.sort(key=lambda r: r["latest"][4], reverse=True)

            if len(inbox_rows) == 0:
                st.info("You have no conversations yet. Use 'Contact seller' on an item to start one.")
            else:
                for row in inbox_rows:
                    item_title = row["item_row"][1] if row["item_row"] is not None else "Item removed"
                    preview = row["latest"][3]
                    if len(preview) > 80:
                        preview = preview[:80] + "…"
                    sent_at = row["latest"][4]
                    other_display = format_user(row["other_party"])

                    with st.container(border=True):
                        if row["unread"] > 0:
                            st.markdown(f"**({row['unread']} new) {item_title}** — {other_display}")
                            st.markdown(f"**{preview}**")
                        else:
                            st.write(f"{item_title} — {other_display}")
                            st.write(preview)
                        st.caption(sent_at)
                        if st.button("Open", key=f"inbox_open_{row['conv_id']}"):
                            st.session_state.active_thread = row["conv_id"]
                            st.rerun()
        else:
            active_id = st.session_state.active_thread
            active_conv = None
            for conv in get_conversations_for_user(current_user):
                if conv[0] == active_id:
                    active_conv = conv
                    break

            if active_conv is None:
                st.warning("Conversation not found.")
                if st.button("Back to inbox", key="thread_back_not_found"):
                    st.session_state.active_thread = None
                    st.rerun()
            else:
                conv_id, conv_item_id, buyer, seller, conv_created_at = active_conv
                other_party = seller if current_user == buyer else buyer

                mark_thread_read(conv_id, current_user)

                if st.button("Back to inbox", key="thread_back"):
                    st.session_state.active_thread = None
                    st.rerun()

                item_row = get_item_or_none(conv_item_id)
                if item_row is None:
                    st.subheader("Item removed")
                else:
                    st.subheader(item_row[1])
                    full_image_path = resolve_item_image(item_row[0], item_row[8])
                    if full_image_path is not None and os.path.exists(full_image_path):
                        st.image(full_image_path, width=200)
                    st.caption(f"Status: {item_row[9]}")

                st.write(f"Conversation with: {format_user(other_party)}")
                st.divider()

                messages = get_thread_messages(conv_id, 1000)

                for msg in messages:
                    msg_id, msg_conv_id, msg_sender, msg_body, msg_sent_at, msg_read_at = msg
                    with st.container(border=True):
                        st.markdown(f"**{format_user(msg_sender)}** · {msg_sent_at}")
                        st.write(msg_body)

                st.divider()
                reply_body = st.text_area(
                    "Your reply",
                    key=f"thread_reply_{conv_id}",
                    placeholder="Write a message…",
                )
                if st.button("Send", key=f"thread_send_{conv_id}"):
                    if send_message(conv_id, current_user, reply_body):
                        st.success("Message sent.")
                        st.rerun()
                    else:
                        st.error("Type a message before sending.")
