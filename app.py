import streamlit as st
import pandas as pd
from datetime import datetime
import pytz
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import urllib.parse
import json

# -------------------------------------------------------------
# PAGE CONFIGURATION
# -------------------------------------------------------------
st.set_page_config(page_title="Makkah Rice Traders", page_icon="🌾", layout="centered")

st.title("🌾 Makkah Rice Traders - Order Portal")
st.markdown("Dukandaron ke liye digital ordering system.")

# APNA WHATSAPP NUMBER YAHAN LIKHEIN (Country code ke sath)
OWNER_WHATSAPP_NUMBER = "923187714954"  # <--- Yahan apna asal WhatsApp number likhein

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

# FETCH LIVE RATES
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
    submit_btn = st.form_submit_button("🚀 Submit Order via WhatsApp")

# -------------------------------------------------------------
# ORDER SUBMISSION & CLEAN WHATSAPP MESSAGE
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
        
        # Clean WhatsApp Message (No links inside)
        wa_message = f"🌾 *NEW ORDER - Makkah Rice Traders*\n\n"
        wa_message += f"🏢 *Dukan:* {shop_name}\n"
        wa_message += f"📞 *Number:* {phone_number}\n"
        wa_message += f"⏰ *Time (PKT):* {current_time}\n\n"
        wa_message += f"*Items Ordered:*\n"
        
        for item in selected_items:
            grand_total += item["total"]
            wa_message += f"- {item['quality']}: {item['quantity']} Bags (Rs. {item['total']:,})\n"
        
        wa_message += f"\n💰 *Grand Total: Rs. {grand_total:,}*"
        
        st.success("🎉 Aapka order generate ho gaya hai! Neeche diye gaye button par click karke owner ko WhatsApp par order bhej dein.")
        
        # Screen Receipt
        st.markdown("---")
        st.markdown("### 🧾 **Order Receipt**")
        st.info(f"**Dukan:** {shop_name}  \n**Mobile:** {phone_number}  \n**Order Time (PKT):** {current_time}")
        
        receipt_list = []
        for item in selected_items:
            receipt_list.append({
                "Quality Name": item["quality"],
                "Price / Bag (Rs.)": f"{item['price_per_bag']:,}",
                "Bags": item["quantity"],
                "Total (Rs.)": f"{item['total']:,}"
            })
        st.table(pd.DataFrame(receipt_list))
        st.markdown(f"### 💰 **Grand Total: Rs. {grand_total:,}**")
        
        # WhatsApp Direct Button
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
# ADMIN AREA (Password Protected Order Approval Portal)
# -------------------------------------------------------------
st.markdown("---")
with st.expander("🔒 Owner / Admin Area (Order Approval & Rates Management)"):
    admin_password = st.text_input("Admin Password Enter Karein:", type="password")
    
    if admin_password == "makkah123":
        st.success("Admin access granted!")
        
        st.markdown("### 📊 Live Rates Table:")
        st.dataframe(df_rates, use_container_width=True)
        
        st.markdown("---")
        st.markdown("### 📥 Approve & Save Order to Google Sheet")
        st.info("WhatsApp par message dekh kar yahan order ki details enter karein aur save button dabayein.")
        
        with st.form("admin_approval_form"):
            adm_shop = st.text_input("Dukan Ka Naam (Shop Name)")
            adm_phone = st.text_input("Dukandar ka Mobile Number")
            adm_quality = st.selectbox("Quality Ordered", df_rates["Quality_Name"].tolist())
            adm_qty = st.number_input("Quantity (Bags)", min_value=1, max_value=1000, value=1)
            
            # Price auto-calculate
            matched_row = df_rates[df_rates["Quality_Name"] == adm_quality]
            price_per_bag = int(matched_row["Price_Per_Bag"].values[0]) if not matched_row.empty else 0
            calc_total = price_per_bag * adm_qty
            
            st.write(f"Estimated Price per Bag: Rs. {price_per_bag:,} | **Total Amount: Rs. {calc_total:,}**")
            
            approve_btn = st.form_submit_button("✅ Verify & Save Order to Google Sheet")
            
        if approve_btn:
            if not adm_shop or not adm_phone:
                st.error("Baraye meharbani dukan ka naam aur mobile number likhein!")
            else:
                pakistan_tz = pytz.timezone("Asia/Karachi")
                adm_time = datetime.now(pakistan_tz).strftime("%Y-%m-%d %H:%M:%S")
                
                try:
                    orders_sheet.append_row([
                        adm_time,
                        adm_shop,
                        adm_phone,
                        adm_quality,
                        adm_qty,
                        calc_total
                    ])
                    st.success(f"🎉 Order kamyabi se Google Sheet ke 'Orders' tab mein save ho gaya hai!")
                    st.balloons()
                except Exception as e:
                    st.error(f"Google Sheet mein save karne mein masla hua: {e}")
                    
    elif admin_password != "":
        st.error("Ghalat password! Baraye meharbani theek password enter karein.")
