import base64
import io
import json
from pydantic import BaseModel, RootModel
import streamlit as st
from PIL import Image
from openai import OpenAI
import requests


scorer_url = "https://cribbage.azurewebsites.net/score_hand_show"
headers = {
    "Accept": "application/json"
}

new_width = 600  # Resize to this for OpenAI


# Expected response structure from OpenAI
class Card(BaseModel):
    initials: str
    description: str


class HandOfCards(BaseModel):
    cards: RootModel[list[Card]]


st.set_page_config(
    page_title="Cribbage Scorer v2",
    layout="wide",
    initial_sidebar_state="collapsed"
)
st.markdown("""
<style>
        /* Hide the header */
        header {visibility: hidden;}

        /* Hide the footer */
        footer {visibility: hidden;}

        /* Center the camera input */
        .stCameraInput div {
            display: flex;
            justify-content: center;
        }

        /* Ensure camera input fits the screen */
        .stCameraInput > div > div {
            width: 100%;
            max-height: 500px; 
            width: auto;
        }
        
        .stCameraInput button {
            padding: 16px 32px; /* Increase button padding */
            font-size: 18px; /* Larger font size for button text */
            background-color: #007BFF; /* Make the button more prominent (blue color) */
            color: white; /* White text for better contrast */
            border: none; /* Remove border */
            font-size: 20px; /* Larger text */
            border-radius: 8px; /* Add rounded corners */
            cursor: pointer; /* Show pointer cursor on hover */
            transition: all 0.3s ease; /* Smooth hover effect */
            width: 100%;
            
        }
        
        /* Adjust padding for a cleaner look */
        .css-1d391kg {padding-top: 0rem;}
        .css-1cpxqw2 {padding-bottom: 0rem;}
</style>
""", unsafe_allow_html=True)

col1, col2 = st.columns([4, 1])  # Adjust the width ratio (3:1 here)


def reset_session_state():
    for key in ["cards", "last_input"]:
        if key in st.session_state:
            del st.session_state[key]


def manage_session_state(img_buffer):
    if "last_input" in st.session_state and \
            st.session_state["last_input"] != img_buffer:
        reset_session_state()

    st.session_state["last_input"] = img_buffer


def detect_cards(image_b64):
    client = OpenAI()

    response = client.beta.chat.completions.parse(
        model="gpt-4o",
        messages=[
            {
                "role": "system",
                "content": [
                    {
                        "type": "text",
                        "text": "You analyse playing cards and return a "
                        "list of cards present in any image.\nReturn "
                        "a response in JSON, using this"
                        "style:\n[\n\"AC\", \"5H\",  "
                        "\"KD\", \"10H\", \"4S\"\n]"
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
        response_format=HandOfCards,
        temperature=1,
        max_tokens=10383,
        top_p=1,
        frequency_penalty=0,
        presence_penalty=0
    )
    assistant_message = response.choices[0].message.content
    return json.loads(assistant_message)


def dicts_from_cards(cards_list):
    by_desc = {}
    by_initials = {}
    for card in cards_list:
        by_desc[card["description"]] = card["initials"]
        by_initials[card["initials"]] = card["description"]
    return by_desc, by_initials


def handle_a_pic(img):

    width, height = img.size
    resize_ratio = (float(width)/new_width)
    new_height = int(height/resize_ratio)

    resized_img = img.resize((new_width, new_height))
    width, height = resized_img.size
    # st.image(resized_img, caption="Here's the image you took.")

    buffer = io.BytesIO()
    resized_img.save(buffer, format="JPEG")
    buffer.seek(0)
    img_bytes = buffer.read()
    b64encoded_img = base64.b64encode(img_bytes).decode("utf-8")

    if "cards" not in st.session_state:
        st.session_state["cards"] = detect_cards(b64encoded_img)

    cards = st.session_state["cards"]
    with col2:

        if len(cards["cards"]) != 5:
            st.write("I can't score the hand as the "
                    "correct number of cards (ie.: 5) is not present.")
        else:
            if "cards" in cards:
                card_choices = cards["cards"]
                cards_by_descs, cards_by_initials = dicts_from_cards(card_choices)
                choice = st.radio("Please choose your starter card "
                                "(We guessed it was the first one):\n",
                                cards_by_descs.keys())
                st.write("You selected:", choice)
            else:
                st.write("Sorry could not see any cards")
                st.write(f"The raw response was: {cards}")

            just_hand = cards_by_initials.copy()
            just_hand.pop(cards_by_descs[choice], None)
            score_req_msg = {"starter": cards_by_descs[choice],
                            "hand": list(just_hand.keys()),
                            "isCrib": False}

            response = requests.post(scorer_url,
                                    json=score_req_msg, headers=headers)

            if "message" in response.json():
                st.write(f"The score was {response.json()['score']} points.")
                scoring_items = response.json()['message'].split('|')
                for item in scoring_items:
                    st.write(item)


# Attempt to capture an image directly from the user's camera.
with col1:
    img_file_buffer = st.camera_input("Take a picture of your cards:")

if img_file_buffer is not None:
    manage_session_state(img_file_buffer)
    an_img = Image.open(img_file_buffer)
    handle_a_pic(an_img)

else:
    uploaded_file = st.file_uploader("Or upload an image",
                                     type=["jpg", "jpeg", "png"])
    if uploaded_file is not None:
        manage_session_state(img_file_buffer)
        an_img = Image.open(uploaded_file)
        handle_a_pic(an_img)
