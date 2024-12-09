import base64
import io
import json
import streamlit as st
from PIL import Image
from openai import OpenAI

st.title("Image Capture and Upload Example")
new_width = 500


def detect_cards(image_b64):
    client = OpenAI()

    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {
            "role": "system",
            "content": [
                {
                "type": "text",
                "text": "You analyse playing cards and return a list of cards present in any image.\nReturn a response in JSON, using this style:\n[\n\"AC\", \"5H\",  \"KD\", \"10H\", \"4S\"\n]"
                }
            ]
            },
            {
            "role": "user",
            "content": [
                {
                "type": "text",
                "text": "What cards are in this image?"
                },
                {
                "type": "image_url",
                "image_url": {
                    "url": f"data:image/jpeg;base64,{image_b64}"
                }
                }
            ]
            }
        ],
        response_format={
            "type": "json_object"
        },
        temperature=1,
        max_tokens=10383,
        top_p=1,
        frequency_penalty=0,
        presence_penalty=0
    )
    assistant_message = response.choices[0].message.content
    return json.loads(assistant_message)


def handle_a_pic(img):
    st.write("This is a beautiful image!")

    width, height = img.size
    st.write(f"Current image size: {width}x{height}")
    resize_ratio = (float(width)/new_width)
    new_height = int(height/resize_ratio)

    # Resize the image
    resized_img = img.resize((new_width, new_height))
    width, height = resized_img.size
    st.image(resized_img, caption="Here's the image you took.")
    st.write(f"New image size: {width}x{height}")

    # Encode the bytes to base64
    buffer = io.BytesIO()
    resized_img.save(buffer, format="JPEG")
    buffer.seek(0)
    img_bytes = buffer.read()
    encoded = base64.b64encode(img_bytes).decode("utf-8")

    cards = detect_cards(encoded)

    if "cards" in cards:
        starter_choices = cards["cards"]
        choice = st.radio("Please choose your starter card:\n",
                          starter_choices)

        st.write("You selected:", choice)
    else:
        st.write("Sorry could not see any cards")
        st.write(f"The raw response was: {cards}")
    

# Attempt to capture an image directly from the user's camera.
img_file_buffer = st.camera_input("Take a photo")

if img_file_buffer is not None:
    # The user took a photo
    an_img = Image.open(img_file_buffer)
    handle_a_pic(an_img)

else:
    # If no camera image was taken, allow file upload instead
    uploaded_file = st.file_uploader("Or upload an image", type=["jpg", "jpeg", "png"])
    if uploaded_file is not None:
        an_img = Image.open(uploaded_file)
        handle_a_pic(an_img)
