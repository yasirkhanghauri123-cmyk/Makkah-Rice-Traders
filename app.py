import streamlit as st
import pandas as pd
from datetime import datetime
import pytz
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import urllib.parse

# -------------------------------------------------------------
# PAGE CONFIGURATION
# -------------------------------------------------------------
st.set_page_config(page_title="Makkah Rice Traders", page_icon="🌾", layout="centered")

st.title("🌾 Makkah Rice Traders - Order Portal")
st.markdown("Dukandaron ke liye digital ordering system.")

OWNER_WHATSAPP_NUMBER = "923176136262"  # <--- Apna WhatsApp number yahan likhein

# Helper Function to convert any GitHub URL to Direct Raw Image Link
def get_raw_image_url(url):
    if not url or not isinstance(url, str):
        return None
    url = url.strip()
    if "github.com" in url and "/blob/" in url:
        url = url.replace("github.com", "raw.githubusercontent.com").replace("/blob/", "/")
    elif "github.com" in url and "/raw/" in url:
        url = url.replace("github.com", "raw.githubusercontent.com").replace("/raw/", "/")
    return url

# -------------------------------------------------------------
# GOOGLE SHEETS CONNECTION
# -------------------------------------------------------------
@st.cache_resource
def init_google_sheet():
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    creds_dict = dict(st.secrets["gcp_service_account"])
    creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
    client = gspread.authorize(creds)
    sheet = client.open("Makkah_Rice_Database")
    return sheet

try:
    gc = init_google_sheet()
    rates_sheet = gc.worksheet("Rates")
    orders_sheet = gc.worksheet("Orders")
except Exception as e:
    st.error(f"Database Connection Error: {e}")
    st.stop()

# FETCH LIVE RATES
data = rates_sheet.get_all_records()
df_rates = pd.DataFrame(data)

if df_rates.empty:
    st.warning("Filhal koi rice quality available nahi hai.")
    st.stop()

# -------------------------------------------------------------
# CUSTOMER ORDER FORM WITH AUTO-FIXED IMAGES
# -------------------------------------------------------------
st.subheader("📝 New Order Form")

with st.form("order_form"):
    shop_name = st.text_input("Dukan Ka Naam (Shop Name)*")
    phone_number = st.text_input("Mobile Number / WhatsApp Number*")
    
    st.markdown("---")
    st.markdown("### Chawal Ki Qualities, Tasweer Aur Quantity Select Karein:")
    
    selected_items = []
    
    for index, row in df_rates.iterrows():
        q_name = row["Quality_Name"]
        q_price = row["Price_Per_Bag"]
        in_stock = str(row["In_Stock"]).strip().capitalize()
        
        # Raw Image URL auto-conversion
        raw_img = get_raw_image_url(row.get("Image_URL", ""))
        
        if in_stock == "Yes":
            col_img, col_info, col_qty = st.columns([1, 2, 1.5])
            
            with col_img:
                if raw_img:
                    try:
                        st.image(raw_img, width=80)
                    except Exception:
                        st.markdown("🌾 *Image Error*")
                else:
                    st.markdown("🌾 *No Image*")
                    
            with col_info:
                st.markdown(f"**{q_name}**")
                st.markdown(f"*Rs. {q_price:,} / Bag*")
                
            with col_qty:
                qty = st.number_input(f"Bags", min_value=0, max_value=1000, value=0, key=f"qty_{index}")
                
            if qty > 0:
                selected_items.append({
                    "quality": q_name,
                    "price_per_bag": q_price,
                    "quantity": qty,
                    "total": q_price * qty
                })
            st.markdown("---")
        else:
            st.markdown(f"~~{q_name}~~ *(Out of Stock)*")
            st.markdown("---")

    submit_btn = st.form_submit_button("🚀 Submit Order via WhatsApp")

# -------------------------------------------------------------
# ORDER SUBMISSION & WHATSAPP MESSAGE
# -------------------------------------------------------------
if submit_btn:
    if not shop_name or not phone_number:
        st.error("Baraye meharbani apna 'Dukan Ka Naam' aur 'Mobile Number' zaroor likhein!")
    elif len(selected_items) == 0:
        st.warning("Kam az kam ek quality ke bags ki quantity select karein.")
    else:
        pakistan_tz = pytz.timezone("Asia/Karachi")
        current_time = datetime.now(pakistan_tz).strftime("%Y-%m-%d %H:%M:%S")
        
        grand_total = 0
        
        wa_message = f"🌾 *NEW ORDER - Makkah Rice Traders*\n\n"
        wa_message += f"🏢 *Dukan:* {shop_name}\n"
        wa_message += f"📞 *Number:* {phone_number}\n"
        wa_message += f"⏰ *Time (PKT):* {current_time}\n\n"
        wa_message += f"*Items Ordered:*\n"
        
        for item in selected_items:
            grand_total += item["total"]
            wa_message += f"- {item['quality']}: {item['quantity']} Bags (Rs. {item['total']:,})\n"
        
        wa_message += f"\n💰 *Grand Total: Rs. {grand_total:,}*"
        
        st.success("🎉 Order generate ho gaya hai!")
        
        # WhatsApp Button
        encoded_message = urllib.parse.quote(wa_message)
        whatsapp_url = f"https://wa.me/{OWNER_WHATSAPP_NUMBER}?text={encoded_message}"
        
        st.markdown(f"""
            <a href="{whatsapp_url}" target="_blank">
                <button style="background-color: #25D366; color: white; padding: 14px 20px; border: none; border-radius: 6px; font-size: 16px; font-weight: bold; cursor: pointer; width: 100%; margin-top: 10px;">
                    📲 Send Order to Owner on WhatsApp
                </button>
            </a>
        """, unsafe_allow_html=True)

# -------------------------------------------------------------
# ADMIN AREA
# -------------------------------------------------------------
st.markdown("---")
with st.expander("🔒 Owner / Admin Area"):
    admin_password = st.text_input("Admin Password Enter Karein:", type="password")
    if admin_password == "makkah123":
        st.success("Admin Access Granted")
        st.dataframe(df_rates, use_container_width=True)
