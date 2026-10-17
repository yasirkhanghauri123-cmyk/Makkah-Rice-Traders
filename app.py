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
st.markdown("Dukandaron ke liye digital ordering system. Aap yahan se apni pasand ki variety aur quantity select karke order place kar sakte hain.")

# APNA WHATSAPP NUMBER YAHAN LIKHEIN (Country code ke sath, e.g., 923001234567)
OWNER_WHATSAPP_NUMBER = "923177107295"  # <--- Yahan apna asal WhatsApp number likhein

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

# Session State for tracking verification
if "order_prepared" not in st.session_state:
    st.session_state.order_prepared = False
if "pending_order_data" not in st.session_state:
    st.session_state.pending_order_data = None

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
    submit_btn = st.form_submit_button("📲 Generate WhatsApp Order Bill")

# -------------------------------------------------------------
# STEP 1: GENERATE WHATSAPP MESSAGE (NO SHEET SAVE YET)
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
        order_rows_to_save = []
        
        wa_message = f"🌾 *NEW ORDER - Makkah Rice Traders*\n\n"
        wa_message += f"🏢 *Dukan:* {shop_name}\n"
        wa_message += f"📞 *Number:* {phone_number}\n"
        wa_message += f"⏰ *Time:* {current_time}\n\n"
        wa_message += f"*Items Ordered:*\n"
        
        for item in selected_items:
            grand_total += item["total"]
            wa_message += f"- {item['quality']}: {item['quantity']} Bags (Rs. {item['total']:,})\n"
            
            order_rows_to_save.append([
                current_time,
                shop_name,
                phone_number,
                item["quality"],
                item["quantity"],
                item["total"]
            ])
        
        wa_message += f"\n💰 *Grand Total: Rs. {grand_total:,}*"
        
        # Save order temporary in session (Not in Google Sheet yet)
        st.session_state.pending_order_data = {
            "rows": order_rows_to_save,
            "wa_message": wa_message,
            "shop_name": shop_name,
            "phone_number": phone_number,
            "current_time": current_time,
            "selected_items": selected_items,
            "grand_total": grand_total
        }
        st.session_state.order_prepared = True

# -------------------------------------------------------------
# STEP 2: DISPLAY RECEIPT & WHATSAPP CONFIRMATION BUTTON
# -------------------------------------------------------------
if st.session_state.order_prepared and st.session_state.pending_order_data:
    order_data = st.session_state.pending_order_data
    
    st.markdown("---")
    st.markdown("### 🧾 **Order Receipt**")
    st.info(f"**Dukan:** {order_data['shop_name']}  \n**Mobile:** {order_data['phone_number']}  \n**Order Time (PKT):** {order_data['current_time']}")
    
    receipt_list = []
    for item in order_data['selected_items']:
        receipt_list.append({
            "Quality Name": item["quality"],
            "Price / Bag (Rs.)": f"{item['price_per_bag']:,}",
            "Bags": item["quantity"],
            "Total (Rs.)": f"{item['total']:,}"
        })
    st.table(pd.DataFrame(receipt_list))
    st.markdown(f"### 💰 **Grand Total: Rs. {order_data['grand_total']:,}**")
    
    encoded_message = urllib.parse.quote(order_data['wa_message'])
    whatsapp_url = f"https://wa.me/{OWNER_WHATSAPP_NUMBER}?text={encoded_message}"
    
    st.warning("⚠️ **Aapka order abhi tak final nahi hua!** Pehle neechay diye gaye button par click karke Owner ko WhatsApp par order bhejein, phir 'Confirm & Save Order' dabayein.")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown(f"""
            <a href="{whatsapp_url}" target="_blank">
                <button style="background-color: #25D366; color: white; padding: 12px; border: none; border-radius: 6px; font-size: 15px; font-weight: bold; cursor: pointer; width: 100%;">
                    📲 1. Send Order via WhatsApp
                </button>
            </a>
        """, unsafe_allow_html=True)
        
    with col2:
        confirm_save = st.button("✅ 2. Confirm Order Saved in Database")

    # Save to Sheet ONLY after pressing Confirm/Send
    if confirm_save:
        try:
            for row in order_data["rows"]:
                orders_sheet.append_row(row)
            
            st.success("🎉 Mubarak ho! Aapka order kamyabi se owner ko chala gaya hai aur Google Sheet mein save ho chuka hai.")
            st.balloons()
            
            # Reset session state
            st.session_state.order_prepared = False
            st.session_state.pending_order_data = None
            
        except Exception as e:
            st.error(f"Google Sheet mein save karne mein masla aaya: {e}")

# -------------------------------------------------------------
# ADMIN AREA (Password Protected)
# -------------------------------------------------------------
st.markdown("---")
with st.expander("🔒 Owner / Admin Area (Rate Management & View)"):
    admin_password = st.text_input("Admin Password Enter Karein:", type="password")
    
    if admin_password == "makkah123":
        st.success("Admin access granted!")
        st.markdown("### Live Rates Table:")
        st.dataframe(df_rates, use_container_width=True)
    elif admin_password != "":
        st.error("Ghalat password! Baraye meharbani theek password enter karein.")
