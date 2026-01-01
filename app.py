import streamlit as st
import cv2
import numpy as np
from PIL import Image
import pillow_avif
import io
import zipfile
import pandas as pd
import requests

# Core processing function
def mask_plate(image_bytes):
    # Convert bytes to PIL then to OpenCV
    image = Image.open(io.BytesIO(image_bytes))
    img = np.array(image.convert('RGB'))
    img = cv2.cvtColor(img, cv2.COLOR_RGB2BGR)
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    
    plate_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_russian_plate_number.xml')
    plates = plate_cascade.detectMultiScale(gray, 1.1, 5)

    for (x, y, w, h) in plates:
        cv2.rectangle(img, (x, y), (x + w, y + h), (255, 255, 255), -1)

    return cv2.cvtColor(img, cv2.COLOR_BGR2RGB)

# --- UI ---
st.set_page_config(page_title="E-Vandi | Excel Bulk Processor", layout="wide")
st.title("🚗 E-Vandi Excel & Bulk Processor")

tabs = st.tabs(["Direct Image Upload", "Excel Link Import"])

# --- Tab 1: Direct Upload (Previous Logic) ---
with tabs[0]:
    uploaded_files = st.file_uploader("Upload Images", type=["avif", "jpg", "png"], accept_multiple_files=True, key="img_up")
    # ... (Same logic as previous response)

# --- Tab 2: Excel Import ---
with tabs[1]:
    st.write("Upload an Excel file with a column named **'Image Link'**.")
    excel_file = st.file_uploader("Upload Excel (.xlsx)", type=["xlsx"])
    
    if excel_file:
        df = pd.read_excel(excel_file)
        st.write("Preview:", df.head())
        
        if "Image Link" in df.columns:
            if st.button("Process All Links from Excel"):
                processed_images = []
                links = df["Image Link"].dropna().tolist()
                
                progress_bar = st.progress(0)
                
                for idx, link in enumerate(links):
                    try:
                        # Download image from link
                        response = requests.get(link, timeout=10)
                        if response.status_code == 200:
                            result_rgb = mask_plate(response.content)
                            
                            # Save to memory
                            res_pil = Image.fromarray(result_rgb)
                            buf = io.BytesIO()
                            res_pil.save(buf, format="PNG")
                            
                            filename = f"vehicle_{idx}.png"
                            processed_images.append((filename, buf.getvalue()))
                    except Exception as e:
                        st.error(f"Failed to download {link}: {e}")
                    
                    progress_bar.progress((idx + 1) / len(links))

                # ZIP Download
                if processed_images:
                    zip_buf = io.BytesIO()
                    with zipfile.ZipFile(zip_buf, "w") as zf:
                        for name, data in processed_images:
                            zf.writestr(name, data)
                    
                    st.success(f"Successfully processed {len(processed_images)} images!")
                    st.download_button(
                        label="Download Excel Results (ZIP)",
                        data=zip_buf.getvalue(),
                        file_name="excel_processed_images.zip",
                        mime="application/zip"
                    )
        else:
            st.error("The Excel file must have a column named 'Image Link'")
