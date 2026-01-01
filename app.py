import streamlit as st
import cv2
import numpy as np
from PIL import Image
import pillow_avif  # Required for AVIF support
import io
import zipfile
import pandas as pd
import requests

# --- Core AI/Processing Function ---
def mask_plate_and_convert_to_avif(image_input):
    """
    Accepts either a PIL Image object or raw image bytes.
    Detects plate, masks it, and returns AVIF bytes.
    """
    # 1. Convert input to a standard PIL Image
    if isinstance(image_input, bytes):
        image = Image.open(io.BytesIO(image_input))
    else:
        image = image_input

    # 2. Convert PIL to OpenCV format (BGR numpy array)
    img_np = np.array(image.convert('RGB'))
    img_cv = cv2.cvtColor(img_np, cv2.COLOR_RGB2BGR)
    gray = cv2.cvtColor(img_cv, cv2.COLOR_BGR2GRAY)
    
    # 3. Detect and Mask
    # Use a pre-trained Haar Cascade classifier for plates
    plate_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_russian_plate_number.xml')
    # Adjust parameters for better detection if needed (scaleFactor, minNeighbors)
    plates = plate_cascade.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=5, minSize=(30,30))

    for (x, y, w, h) in plates:
        # Draw a filled white rectangle (-1 thickness) over the detected area
        cv2.rectangle(img_cv, (x, y), (x + w, y + h), (255, 255, 255), -1)

    # 4. Convert back to PIL RGB format
    result_rgb = cv2.cvtColor(img_cv, cv2.COLOR_BGR2RGB)
    result_pil = Image.fromarray(result_rgb)
    
    # 5. Save as AVIF bytes to memory buffer
    avif_buffer = io.BytesIO()
    # "quality=85" is a good balance for AVIF, adjust between 0-100 as needed
    result_pil.save(avif_buffer, format="AVIF", quality=85)
    return avif_buffer.getvalue()


# --- Main Streamlit App UI ---
st.set_page_config(page_title="E-Vandi | 360° Prep Tool", page_icon="🚗", layout="wide")

st.title("🚗 E-Vandi: 360° Image Preparation Tool")
st.markdown("""
This tool prepares vehicle images for 360° views by:
1.  Automatically masking license plates to remove branding or private info.
2.  Converting all outputs to the high-efficiency **AVIF** format.
""")

# Create tabs for different upload methods
tabs = st.tabs(["📤 Direct Image Upload", "📊 Excel Link Import"])

# ===========================
# TAB 1: Direct Image Upload
# ===========================
with tabs[0]:
    st.write("Upload individual frames (AVIF, JPG, PNG).")
    uploaded_files = st.file_uploader("Choose images...", type=["avif", "jpg", "jpeg", "png"], accept_multiple_files=True)

    if uploaded_files:
        processed_avifs = []
        st.markdown("---")
        st.subheader(f"Processing {len(uploaded_files)} frames...")
        progress_bar = st.progress(0)
        
        # Create a grid for gallery preview
        cols = st.columns(4)
        
        for idx, uploaded_file in enumerate(uploaded_files):
            # Open and process
            input_image = Image.open(uploaded_file)
            avif_bytes = mask_plate_and_convert_to_avif(input_image)
            
            # Create a new filename with .avif extension
            new_filename = uploaded_file.name.rsplit('.', 1)[0] + "_processed.avif"
            processed_avifs.append((new_filename, avif_bytes))
            
            # Show preview in grid (convert bytes back to image for display)
            with cols[idx % 4]:
                st.image(avif_bytes, caption=new_filename, use_container_width=True)
            
            progress_bar.progress((idx + 1) / len(uploaded_files))
            
        # ZIP Download Button
        if processed_avifs:
            zip_buf = io.BytesIO()
            with zipfile.ZipFile(zip_buf, "w", zipfile.ZIP_DEFLATED) as zf:
                for name, data in processed_avifs:
                    zf.writestr(name, data)
            
            st.success("✅ All frames processed into AVIF format!")
            st.download_button(
                label="⬇️ Download All AVIFs (ZIP)",
                data=zip_buf.getvalue(),
                file_name="evandi_360_frames_avif.zip",
                mime="application/zip",
                type="primary"
            )

# ===========================
# TAB 2: Excel Import
# ===========================
with tabs[1]:
    st.write("Upload an Excel file (.xlsx) containing a column named **'Image Link'**.")
    excel_file = st.file_uploader("Choose Excel file...", type=["xlsx"])
    
    if excel_file:
        df = pd.read_excel(excel_file)
        st.write("Data Preview:", df.head())
        
        if "Image Link" in df.columns:
            links = df["Image Link"].dropna().tolist()
            st.info(f"Found {len(links)} image links found in file.")
            
            if st.button(f"🚀 Process {len(links)} Links from Excel"):
                processed_avifs_xl = []
                progress_bar_xl = st.progress(0)
                status_text = st.empty()
                
                for idx, link in enumerate(links):
                    status_text.text(f"Downloading & Processing: {link}...")
                    try:
                        # Download image
                        response = requests.get(link, timeout=15)
                        response.raise_for_status() # Raise exception for bad status codes
                        
                        # Process bytes directly
                        avif_bytes = mask_plate_and_convert_to_avif(response.content)
                        
                        # Create standardized filename
                        filename = f"frame_{str(idx+1).zfill(3)}.avif"
                        processed_avifs_xl.append((filename, avif_bytes))
                        
                    except Exception as e:
                        st.warning(f"⚠️ Could not process link {idx+1}: {e}")
                    
                    progress_bar_xl.progress((idx + 1) / len(links))
                
                status_text.text("Processing complete!")
                
                # ZIP Download for Excel results
                if processed_avifs_xl:
                    zip_buf_xl = io.BytesIO()
                    with zipfile.ZipFile(zip_buf_xl, "w", zipfile.ZIP_DEFLATED) as zf:
                        for name, data in processed_avifs_xl:
                            zf.writestr(name, data)
                    
                    st.success(f"✅ Successfully processed {len(processed_avifs_xl)} images into AVIF!")
                    st.download_button(
                        label="⬇️ Download Excel Results (ZIP)",
                        data=zip_buf_xl.getvalue(),
                        file_name="evandi_excel_avifs.zip",
                        mime="application/zip",
                        type="primary"
                    )
        else:
            st.error("❌ Error: Column 'Image Link' not found in the Excel file.")
