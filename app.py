import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime
import os

# ------------------------------
# File paths for local storage
# ------------------------------
INVENTORY_FILE = "inventory_data.csv"
SALES_FILE = "sales_data.csv"

# ------------------------------
# Helper functions for persistence
# ------------------------------
def load_data():
    """Load data from CSV files if they exist, else create empty DataFrames."""
    if os.path.exists(INVENTORY_FILE):
        inventory = pd.read_csv(INVENTORY_FILE)
    else:
        inventory = pd.DataFrame(columns=["Product ID", "Product Name", "Price", "Quantity", "Category"])

    if os.path.exists(SALES_FILE):
        sales = pd.read_csv(SALES_FILE)
    else:
        sales = pd.DataFrame(columns=["Date", "Customer Name", "Product ID", "Product Name", "Quantity Sold", "Total Price"])

    return inventory, sales

def save_data():
    """Save data to CSV files."""
    st.session_state.inventory.to_csv(INVENTORY_FILE, index=False)
    st.session_state.sales.to_csv(SALES_FILE, index=False)

# ------------------------------
# Initialize session state
# ------------------------------
if "inventory" not in st.session_state or "sales" not in st.session_state:
    inventory, sales = load_data()
    st.session_state.inventory = inventory
    st.session_state.sales = sales

# ------------------------------
# Core functions
# ------------------------------
def add_product(pid, name, price, qty, category):
    new_row = pd.DataFrame({
        "Product ID": [pid],
        "Product Name": [name],
        "Price": [price],
        "Quantity": [qty],
        "Category": [category]
    })
    st.session_state.inventory = pd.concat([st.session_state.inventory, new_row], ignore_index=True)
    save_data()

def record_sale(customer, pid, qty):
    product = st.session_state.inventory[st.session_state.inventory["Product ID"] == pid]
    if product.empty:
        st.error("Product ID not found!")
        return
    stock_qty = int(product["Quantity"].values[0])
    price = float(product["Price"].values[0])
    name = product["Product Name"].values[0]

    if qty > stock_qty:
        st.error("Not enough stock available!")
        return

    total_price = price * qty

    new_sale = pd.DataFrame({
        "Date": [datetime.now().strftime("%Y-%m-%d %H:%M:%S")],
        "Customer Name": [customer],
        "Product ID": [pid],
        "Product Name": [name],
        "Quantity Sold": [qty],
        "Total Price": [total_price]
    })

    # Update data
    st.session_state.sales = pd.concat([st.session_state.sales, new_sale], ignore_index=True)
    st.session_state.inventory.loc[st.session_state.inventory["Product ID"] == pid, "Quantity"] = stock_qty - qty

    save_data()
    st.success(f"Sale recorded for {customer}!")

def delete_sale(index_to_delete):
    """Delete a sale by its index from the sales DataFrame and update CSV."""
    if 0 <= index_to_delete < len(st.session_state.sales):
        deleted_row = st.session_state.sales.iloc[index_to_delete]
        pid = deleted_row["Product ID"]
        qty_sold = deleted_row["Quantity Sold"]

        # Restore the stock quantity in inventory
        if pid in st.session_state.inventory["Product ID"].values:
            st.session_state.inventory.loc[
                st.session_state.inventory["Product ID"] == pid, "Quantity"
            ] += qty_sold

        # Drop the sale from the sales DataFrame
        st.session_state.sales = st.session_state.sales.drop(index_to_delete).reset_index(drop=True)

        # Save updated data
        save_data()

        st.success(f"✅ Sale record for product '{deleted_row['Product Name']}' has been deleted successfully.")
    else:
        st.warning("Invalid sale index selected.")

def calculate_revenue():
    if st.session_state.sales.empty:
        return 0.0
    return st.session_state.sales["Total Price"].sum()

# ------------------------------
# Streamlit UI
# ------------------------------
st.title("🛒 Retail Billing & Inventory Management System")

menu = st.sidebar.selectbox("Menu", [
    "🏠 Dashboard",
    "📦 Manage Inventory",
    "💰 Record Sale",
    "📊 Reports",
    "🔍 Search Data",
    "👥 Customer Data"
])

# ------------------------------
# Dashboard
# ------------------------------
if menu == "🏠 Dashboard":
    st.subheader("Dashboard Overview")
    st.metric("Total Products", len(st.session_state.inventory))
    st.metric("Total Sales", len(st.session_state.sales))
    st.metric("Total Revenue", f"${calculate_revenue():,.2f}")

# ------------------------------
# Inventory Management
# ------------------------------
elif menu == "📦 Manage Inventory":
    st.subheader("Add / Update Inventory")

    with st.form("add_product_form"):
        pid = st.text_input("Product ID")
        name = st.text_input("Product Name")
        price = st.number_input("Price", min_value=0.0, step=0.01)
        qty = st.number_input("Quantity", min_value=0, step=1)
        category = st.text_input("Category")
        submitted = st.form_submit_button("Add Product")

        if submitted:
            if pid and name:
                add_product(pid, name, price, qty, category)
                st.success(f"Added product: {name}")
            else:
                st.warning("Please fill all fields.")

    st.subheader("Current Inventory")
    st.dataframe(st.session_state.inventory)

    # --- Download Inventory Data ---
    if not st.session_state.inventory.empty:
        st.download_button(
            label="⬇️ Download Inventory Data as CSV",
            data=st.session_state.inventory.to_csv(index=False).encode('utf-8'),
            file_name="inventory_data.csv",
            mime="text/csv"
        )

# ------------------------------
# Record Sale
# ------------------------------
elif menu == "💰 Record Sale":
    st.subheader("New Sale Entry")

    with st.form("sale_form"):
        customer = st.text_input("Customer Name")
        pid = st.text_input("Product ID")
        qty = st.number_input("Quantity Sold", min_value=1, step=1)
        submitted = st.form_submit_button("Record Sale")

        if submitted:
            if customer and pid:
                record_sale(customer, pid, qty)
            else:
                st.warning("Please fill all fields.")

    st.subheader("Sales Data")

    if not st.session_state.sales.empty:
        st.dataframe(st.session_state.sales)

        delete_index = st.number_input(
            "Enter the sale row index to delete (starting from 0):",
            min_value=0,
            max_value=len(st.session_state.sales) - 1,
            step=1
        )

        if st.button("🗑️ Delete Selected Sale"):
            delete_sale(delete_index)
    else:
        st.info("No sales records available yet.")

# ------------------------------
# Reports
# ------------------------------
elif menu == "📊 Reports":
    st.subheader("Sales & Revenue Report")
    total_rev = calculate_revenue()
    st.metric("Total Revenue", f"${total_rev:,.2f}")

    if not st.session_state.sales.empty:
        sales_summary = st.session_state.sales.groupby("Product Name")["Total Price"].sum().reset_index()
        st.bar_chart(sales_summary.set_index("Product Name"))

        # --- Download Sales Data ---
        st.download_button(
            label="⬇️ Download Sales Data as CSV",
            data=st.session_state.sales.to_csv(index=False).encode('utf-8'),
            file_name="sales_data.csv",
            mime="text/csv"
        )
    else:
        st.info("No sales yet to show.")

# ------------------------------
# Search Data
# ------------------------------
elif menu == "🔍 Search Data":
    st.subheader("Search for Particular Data")

    search_type = st.radio("Select what you want to search:", ["Inventory (Product)", "Sales", "Customer"])
    query = st.text_input("Enter your search keyword (Product ID, Name, or Customer Name):")

    if st.button("Search"):
        if search_type == "Inventory (Product)":
            result = st.session_state.inventory[
                st.session_state.inventory.apply(lambda row: query.lower() in row.astype(str).str.lower().values, axis=1)
            ]
            st.dataframe(result if not result.empty else pd.DataFrame({"Result": ["No matching product found."]}))

        elif search_type == "Sales":
            result = st.session_state.sales[
                st.session_state.sales.apply(lambda row: query.lower() in row.astype(str).str.lower().values, axis=1)
            ]
            st.dataframe(result if not result.empty else pd.DataFrame({"Result": ["No matching sales found."]}))

        elif search_type == "Customer":
            result = st.session_state.sales[st.session_state.sales["Customer Name"].str.contains(query, case=False, na=False)]
            st.dataframe(result if not result.empty else pd.DataFrame({"Result": ["No data found for this customer."]}))

# ------------------------------
# Customer Data
# ------------------------------
elif menu == "👥 Customer Data":
    st.subheader("Customer Purchase History")

    if not st.session_state.sales.empty:
        customers = st.session_state.sales["Customer Name"].unique().tolist()
        selected_customer = st.selectbox("Select Customer", customers)
        customer_data = st.session_state.sales[st.session_state.sales["Customer Name"] == selected_customer]
        st.dataframe(customer_data)

        # --- Download Customer Purchase History ---
        st.download_button(
            label="⬇️ Download This Customer's Data as CSV",
            data=customer_data.to_csv(index=False).encode('utf-8'),
            file_name=f"{selected_customer}_purchases.csv",
            mime="text/csv"
        )
    else:
        st.info("No customer data available yet.")
