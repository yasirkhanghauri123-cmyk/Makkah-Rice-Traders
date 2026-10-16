import streamlit as st
import pandas as pd
from datetime import datetime
import gspread
from oauth2client.service_account import ServiceAccountCredentials

# -------------------------------------------------------------
# PAGE CONFIGURATION
# -------------------------------------------------------------
st.set_page_config(page_title="Makkah Rice Traders", page_icon="🌾", layout="centered")

st.title("🌾 Makkah Rice Traders - Order Portal")
st.markdown("Dukandaron ke liye digital ordering system. Aap yahan se apni pasand ki variety aur quantity select karke order place kar sakte hain.")

# -------------------------------------------------------------
# GOOGLE SHEETS CONNECTION (Caches connection for speed)
# -------------------------------------------------------------
@st.cache_resource
def init_google_sheet():
    # Streamlit secrets se credentials uthayega (Neeche step bataya gaya hai)
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    creds_dict = dict(st.secrets["gcp_service_account"])
    creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
    client = gspread.authorize(creds)
    
    # Google Sheet ka naam jo aapne banayi hai
    sheet = client.open("Makkah_Rice_Database")
    return sheet

try:
    gc = init_google_sheet()
    rates_sheet = gc.worksheet("Rates")
    orders_sheet = gc.worksheet("Orders")
except Exception as e:
    st.error(f"Database Connection Error: {e}")
    st.info("Baraye meharbani Streamlit secrets mein Google Sheets ki JSON credentials configure karein.")
    st.stop()

# -------------------------------------------------------------
# FETCH LIVE RATES FROM GOOGLE SHEET
# -------------------------------------------------------------
data = rates_sheet.get_all_records()
df_rates = pd.DataFrame(data)

if df_rates.empty:
    st.warning("Filhal koi rice quality available nahi hai. Baraye meharbani Google Sheet mein rates update karein.")
    st.stop()

# -------------------------------------------------------------
# CUSTOMER ORDER FORM
# -------------------------------------------------------------
st.subheader("📝 New Order Form")

with st.form("order_form"):
    shop_name = st.text_input("Dukan Ka Naam (Shop Name)*")
    phone_number = st.text_input("Mobile Number / WhatsApp Number*")
    
    st.markdown("---")
    st.markdown("### Chawal Ki Qualities Aur Quantity Select Karein:")
    
    selected_items = []
    
    # Har quality ke liye ek input field generate hogi (Chahe 12 hon ya 19)
    for index, row in df_rates.iterrows():
        q_name = row["Quality_Name"]
        q_price = row["Price_Per_Bag"]
        in_stock = str(row["In_Stock"]).strip().capitalize()
        
        if in_stock == "Yes":
            col1, col2 = st.columns([2, 1])
            with col1:
                st.markdown(f"**{q_name}**  \n*Rs. {q_price:,} / Bag*")
            with col2:
                qty = st.number_input(f"Bags ({q_name})", min_value=0, max_value=1000, value=0, key=f"qty_{index}")
                
            if qty > 0:
                selected_items.append({
                    "quality": q_name,
                    "price_per_bag": q_price,
                    "quantity": qty,
                    "total": q_price * qty
                })
        else:
            st.markdown(f"~~{q_name}~~ *(Out of Stock)*")

    st.markdown("---")
    submit_btn = st.form_submit_button("🚀 Place Order Now")

# -------------------------------------------------------------
# ORDER SUBMISSION LOGIC
# -------------------------------------------------------------
if submit_btn:
    if not shop_name or not phone_number:
        st.error("Baraye meharbani apna 'Dukan Ka Naam' aur 'Mobile Number' zaroor likhein!")
    elif len(selected_items) == 0:
        st.warning("Kam az kam ek quality ke bags ki quantity select karein.")
    else:
        current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        order_rows_to_save = []
        grand_total = 0
        
        for item in selected_items:
            grand_total += item["total"]
            order_rows_to_save.append([
                current_time,
                shop_name,
                phone_number,
                item["quality"],
                item["quantity"],
                item["total"]
            ])
        
        # Google Sheet ke 'Orders' tab mein data append karna
        try:
            for row in order_rows_to_save:
                orders_sheet.append_row(row)
            
            st.success(f"🎉 Shukriya! Aapka order kamyabi se record ho gaya hai. Grand Total: Rs. {grand_total:,}")
            st.balloons()
        except Exception as e:
            st.error(f"Order save karne mein masla hua: {e}")

# -------------------------------------------------------------
# ADMIN VIEW (Rates Check Karne Ke Liye)
# -------------------------------------------------------------
with st.expander("🔒 Owner / Admin Area (Current Rates View)"):
    st.markdown("Aap apni **Google Sheet** (`Makkah_Rice_Database`) mein ja kar jab chahein rates change kar sakte hain ya nayi qualities add kar sakte hain. Yahan live rates show ho rahe hain:")
    st.dataframe(df_rates, use_container_width=True)