import streamlit as st
import pymongo
import os
import uuid
from bson.objectid import ObjectId
from PIL import Image

# MongoDB setup
MONGO_URL = "mongodb+srv://tintin:tintin@cluster0.qot4y.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0"
client = pymongo.MongoClient(MONGO_URL)
db = client['food_ordering']
users_col = db['users']
categories_col = db['categories']
products_col = db['products']
orders_col = db['orders']
settings_col = db['settings']

# Ensure image directory exists
os.makedirs("images", exist_ok=True)

# Session state defaults
for key in ['role', 'username', 'cart']:
    if key not in st.session_state:
        st.session_state[key] = [] if key == 'cart' else None

# Authentication
def register_user(username, password):
    if not username or not password:
        st.warning('Please enter both username and password.')
        return
    if users_col.find_one({'username': username}):
        st.warning('⚠️ Username already exists.')
    else:
        users_col.insert_one({'username': username, 'password': password, 'role': 'client'})
        st.success('✅ Registration successful. Please log in.')

def login_user(username, password):
    if not username or not password:
        st.warning('Please enter both username and password.')
        return
    user = users_col.find_one({'username': username, 'password': password})
    if user:
        st.session_state.username = username
        st.session_state.role = user['role']
        st.success(f"✅ Logged in as **{st.session_state.role}**")
    else:
        st.error('❌ Invalid username or password')

def logout():
    st.session_state.username = None
    st.session_state.role = None
    st.session_state.cart = []

# Admin Panels
def admin_dashboard():
    st.header("📊 Admin Dashboard")
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Users", users_col.count_documents({'role': 'client'}))
    col2.metric("Categories", categories_col.count_documents({}))
    col3.metric("Products", products_col.count_documents({}))
    col4.metric("Orders", orders_col.count_documents({}))

def manage_categories():
    st.header("📂 Category Management")
    categories = list(categories_col.find({}))
    for cat in categories:
        col1, col2 = st.columns([4, 1])
        col1.write(f"**{cat['name']}**")
        if col2.button("🗑️ Delete", key=str(cat['_id'])):
            categories_col.delete_one({'_id': cat['_id']})
            st.success("✅ Category deleted")
            st.experimental_rerun()
    new_cat = st.text_input("➕ Add New Category")
    if st.button("Add Category"):
        if new_cat.strip():
            categories_col.insert_one({'name': new_cat})
            st.success("✅ Category added")
            st.experimental_rerun()
        else:
            st.warning("Please enter a category name.")

def manage_products():
    st.header("🍽️ Product Management")
    products = list(products_col.find({}))
    for prod in products:
        col1, col2 = st.columns([5, 1])
        if prod.get('image') and os.path.exists(prod['image']):
            col1.image(prod['image'], width=100)
        col1.write(f"**{prod['name']}** - ${prod['price']} ({prod['category']})")
        col1.caption(prod.get('description', 'No description'))
        if col2.button("🗑️ Delete", key=f"del_{prod['_id']}"):
            if prod.get('image') and os.path.exists(prod['image']):
                os.remove(prod['image'])  # Remove image file
            products_col.delete_one({'_id': prod['_id']})
            st.success("✅ Product deleted")
            st.experimental_rerun()

    st.subheader("➕ Add New Product")
    name = st.text_input("Product Name")
    price = st.number_input("Price", 0.0)
    description = st.text_area("Description")
    category = st.selectbox("Category", [c['name'] for c in categories_col.find({})])
    image_file = st.file_uploader("Upload Product Image", type=["png", "jpg", "jpeg"])

    if st.button("Add Product"):
        if name and category:
            image_path = ""
            if image_file:
                filename = f"images/{uuid.uuid4()}_{image_file.name}"
                with open(filename, "wb") as f:
                    f.write(image_file.getbuffer())
                image_path = filename
            products_col.insert_one({
                'name': name,
                'price': price,
                'description': description,
                'category': category,
                'image': image_path
            })
            st.success("✅ Product added")
            st.experimental_rerun()
        else:
            st.warning("Please enter product name and category.")

def manage_orders():
    st.header("📦 Order Management")
    orders = list(orders_col.find({}))
    if not orders:
        st.info("No orders yet.")
        return
    for order in orders:
        st.markdown(f"### 🛒 Order by `{order['username']}` | Total: **${order['total']}**")
        for item in order['items']:
            product = products_col.find_one({'_id': ObjectId(item['_id'])})
            if product and product.get('image') and os.path.exists(product['image']):
                st.image(product['image'], width=80)
            st.write(f"**{item['name']}** - ${item['price']} x {item['qty']}")
        status = st.selectbox(
            "Update Status",
            ["Confirmed", "Cooking", "On the way", "Delivered"],
            index=["Confirmed", "Cooking", "On the way", "Delivered"].index(order.get('status', 'Confirmed')),
            key=f"status_{order['_id']}"
        )
        col1, col2 = st.columns(2)
        if col1.button("✅ Update Status", key=f"update_{order['_id']}"):
            orders_col.update_one({'_id': order['_id']}, {'$set': {'status': status}})
            st.success("Status updated")
            st.experimental_rerun()
        if col2.button("✅ Mark Complete", key=f"complete_{order['_id']}"):
            orders_col.delete_one({'_id': order['_id']})
            st.success("Order completed and removed")

def manage_users():
    st.header("👥 User Management")
    users = list(users_col.find({'role': 'client'}))
    for user in users:
        col1, col2 = st.columns([4, 1])
        col1.write(f"**{user['username']}**")
        if col2.button("🗑️ Delete", key=str(user['_id'])):
            users_col.delete_one({'_id': user['_id']})
            st.success("✅ User deleted")
            st.experimental_rerun()

def system_settings():
    st.header("⚙️ System Settings")
    settings = settings_col.find_one()
    if not settings:
        settings_col.insert_one({'site_name': 'My Food Shop'})
        settings = settings_col.find_one()
    site_name = st.text_input("Site Name", settings['site_name'])
    if st.button("Save Settings"):
        settings_col.update_one({}, {'$set': {'site_name': site_name}})
        st.success("✅ Settings saved")

# Client Panels
def show_menu():
    st.header("🍽️ Menu")
    products = list(products_col.find({}))
    for prod in products:
        with st.container():
            col1, col2 = st.columns([2, 1])
            if prod.get('image') and os.path.exists(prod['image']):
                col1.image(prod['image'], width=150)
            col1.write(f"**{prod['name']}** - ${prod['price']}")
            col1.caption(prod.get('description', 'No description'))
            if col2.button("🛒 Add to Cart", key=str(prod['_id'])):
                # Prevent duplicate entries in cart
                for item in st.session_state.cart:
                    if item['_id'] == str(prod['_id']):
                        item['qty'] += 1
                        break
                else:
                    st.session_state.cart.append({'_id': str(prod['_id']), 'name': prod['name'], 'price': prod['price'], 'qty': 1})
                st.success(f"{prod['name']} added to cart")

def view_cart():
    st.header("🛒 Cart")
    if not st.session_state.cart:
        st.info("Your cart is empty.")
        return
    total = sum(item['price'] * item['qty'] for item in st.session_state.cart)
    for item in st.session_state.cart:
        st.write(f"{item['name']} - ${item['price']} x {item['qty']}")
    st.write(f"**Total:** ${total}")
    with st.form("checkout"):
        address = st.text_input("Address")
        phone = st.text_input("Phone Number")
        submit = st.form_submit_button("Place Order")
        if submit:
            if not address or not phone:
                st.warning("Please fill in address and phone.")
            else:
                orders_col.insert_one({
                    'username': st.session_state.username,
                    'items': st.session_state.cart,
                    'total': total,
                    'address': address,
                    'phone': phone,
                    'status': 'Confirmed'
                })
                st.session_state.cart = []
                st.success("✅ Order placed successfully!")

def order_status():
    st.header("📦 My Orders")
    orders = list(orders_col.find({'username': st.session_state.username}))
    if not orders:
        st.info("No orders yet.")
        return
    for order in orders:
        st.markdown(f"### 🛍️ Total: **${order['total']}** | Status: `{order.get('status', 'Confirmed')}`")
        for item in order['items']:
            product = products_col.find_one({'_id': ObjectId(item['_id'])})
            if product and product.get('image') and os.path.exists(product['image']):
                st.image(product['image'], width=80)
            st.write(f"**{item['name']}** - ${item['price']} x {item['qty']}")

# Main Interface
st.set_page_config(page_title="Food Ordering App", layout="wide")
st.title("🍽️ Food Ordering System")

if st.session_state.username:
    st.sidebar.write(f"👤 Logged in as **{st.session_state.username}**")
    if st.sidebar.button("🚪 Logout"):
        logout()
else:
    tab = st.sidebar.radio("Choose", ["Login", "Register"])
    username = st.sidebar.text_input("Username")
    password = st.sidebar.text_input("Password", type='password')
    if tab == "Login":
        if st.sidebar.button("Login"):
            login_user(username, password)
    else:
        if st.sidebar.button("Register"):
            register_user(username, password)

if st.session_state.role == 'admin':
    tab = st.selectbox("Admin Panel", ["Dashboard", "Categories", "Products", "Orders", "Users", "Settings"])
    {
        "Dashboard": admin_dashboard,
        "Categories": manage_categories,
        "Products": manage_products,
        "Orders": manage_orders,
        "Users": manage_users,
        "Settings": system_settings
    }[tab]()
elif st.session_state.role == 'client':
    tab = st.selectbox("Client Panel", ["Menu", "Cart", "Order Status"])
    {
        "Menu": show_menu,
        "Cart": view_cart,
        "Order Status": order_status
    }[tab]()
else:
    st.write("🔑 Please login or register to continue.")
