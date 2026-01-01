import streamlit as st
import cv2
import numpy as np
from PIL import Image

def mask_plate(image):
    # Convert PIL to OpenCV format
    img = np.array(image.convert('RGB'))
    img = cv2.cvtColor(img, cv2.COLOR_RGB2BGR)
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

    # Load the pre-trained License Plate detector
    # You can download this XML from OpenCV's GitHub
    plate_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_russian_plate_number.xml')
    
    # Detect plates
    plates = plate_cascade.detectMultiScale(gray, 1.1, 4)

    for (x, y, w, h) in plates:
        # Draw a white rectangle over the plate
        cv2.rectangle(img, (x, y), (x + w, y + h), (255, 255, 255), -1)

    # Convert back to RGB for Streamlit
    return cv2.cvtColor(img, cv2.COLOR_BGR2RGB)

st.set_page_config(page_title="E-Vandi Plate Eraser", layout="centered")

st.title("🚗 Vehicle Plate Privacy Masker")
st.write("Upload a vehicle image to automatically white-out the number plate.")

uploaded_file = st.file_uploader("Choose an image...", type=["jpg", "jpeg", "png"])

if uploaded_file is not None:
    input_image = Image.open(uploaded_file)
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("Original Image")
        st.image(input_image, use_container_width=True)
        
    with col2:
        st.subheader("Processed Image")
        processed_img = mask_plate(input_image)
        st.image(processed_img, use_container_width=True)
        
        # Download button
        result_img = Image.fromarray(processed_img)
        # Save to buffer to allow download
        import io
        buf = io.BytesIO()
        result_img.save(buf, format="PNG")
        byte_im = buf.getvalue()
        
        st.download_button(
            label="Download Masked Image",
            data=byte_im,
            file_name="masked_plate.png",
            mime="image/png"
        )
