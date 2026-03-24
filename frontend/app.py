import os

import requests
import streamlit as st
from dotenv import load_dotenv

load_dotenv()

API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000")

st.set_page_config(page_title="CRAG Assistant", layout="wide")


def get_headers():
    token = st.session_state.get("token")
    return {"Authorization": f"Bearer {token}"} if token else {}


def api_request(method: str, path: str, **kwargs):
    url = f"{API_BASE_URL}{path}"
    response = requests.request(method, url, timeout=60, **kwargs)
    if response.status_code >= 400:
        try:
            detail = response.json().get("detail", response.text)
        except ValueError:
            detail = response.text
        raise RuntimeError(detail)
    if response.content:
        return response.json()
    return None


def init_state():
    defaults = {
        "token": None,
        "user": None,
        "selected_conversation_id": None,
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


def render_auth():
    st.title("CRAG Document QA")
    tab_login, tab_signup = st.tabs(["Login", "Sign Up"])

    with tab_login:
        with st.form("login_form"):
            email = st.text_input("Email", key="login_email")
            password = st.text_input("Password", type="password", key="login_password")
            submitted = st.form_submit_button("Login")
            if submitted:
                data = api_request("POST", "/auth/login", json={"email": email, "password": password})
                st.session_state.token = data["access_token"]
                st.session_state.user = data["user"]
                st.rerun()

    with tab_signup:
        with st.form("signup_form"):
            email = st.text_input("Email", key="signup_email")
            password = st.text_input("Password", type="password", key="signup_password")
            submitted = st.form_submit_button("Create Account")
            if submitted:
                api_request("POST", "/auth/register", json={"email": email, "password": password})
                st.success("Account created. Please log in.")


def render_sidebar():
    st.sidebar.subheader("Account")
    st.sidebar.write(st.session_state.user["email"])
    if st.sidebar.button("Logout"):
        st.session_state.token = None
        st.session_state.user = None
        st.session_state.selected_conversation_id = None
        st.rerun()

    st.sidebar.subheader("Conversations")
    conversations = api_request("GET", "/conversations", headers=get_headers())
    if st.sidebar.button("New Chat"):
        st.session_state.selected_conversation_id = None
    for conversation in conversations:
        if st.sidebar.button(conversation["title"], key=f"conv_{conversation['id']}"):
            st.session_state.selected_conversation_id = conversation["id"]


def render_documents():
    st.subheader("Documents")
    upload = st.file_uploader("Upload PDF, DOCX, TXT, or MD", type=["pdf", "docx", "txt", "md"])
    if upload and st.button("Upload Document"):
        files = {"file": (upload.name, upload, upload.type)}
        api_request("POST", "/documents/upload", headers=get_headers(), files=files)
        st.success("Document uploaded")
        st.rerun()

    documents = api_request("GET", "/documents", headers=get_headers())
    if not documents:
        st.info("No documents uploaded yet.")
        return documents

    for document in documents:
        cols = st.columns([5, 1])
        cols[0].write(document["filename"])
        if cols[1].button("Delete", key=f"delete_doc_{document['id']}"):
            api_request("DELETE", f"/documents/{document['id']}", headers=get_headers())
            st.rerun()
    return documents


def render_citations(citations):
    doc_sources = [item for item in citations if item["source_type"] == "document"]
    web_sources = [item for item in citations if item["source_type"] == "web"]

    if doc_sources:
        st.markdown("**Document Sources**")
        for citation in doc_sources:
            page = f" (page {citation['page_number']})" if citation.get("page_number") is not None else ""
            st.caption(f"{citation['title']}{page}: {citation['snippet']}")

    if web_sources:
        st.markdown("**Web Sources**")
        for citation in web_sources:
            st.caption(f"[{citation['title']}]({citation['url']}): {citation['snippet']}")


def render_feedback(message_id: int):
    with st.form(f"feedback_form_{message_id}"):
        cols = st.columns([2, 4, 1])
        sentiment = cols[0].radio(
            "Feedback",
            options=["Helpful", "Not Helpful"],
            horizontal=True,
            key=f"sentiment_{message_id}",
            label_visibility="collapsed",
        )
        comment = cols[1].text_input("Comment", key=f"comment_{message_id}", label_visibility="collapsed")
        submitted = cols[2].form_submit_button("Send")
        if submitted:
            api_request(
                "POST",
                "/feedback",
                headers=get_headers(),
                json={
                    "message_id": message_id,
                    "is_positive": sentiment == "Helpful",
                    "comment": comment or None,
                },
            )
            st.success("Feedback saved")


def render_chat(documents):
    st.subheader("Chat")
    selected_ids = st.multiselect(
        "Document scope",
        options=[doc["id"] for doc in documents],
        format_func=lambda doc_id: next(doc["filename"] for doc in documents if doc["id"] == doc_id),
    )

    if st.session_state.selected_conversation_id:
        detail = api_request(
            "GET",
            f"/conversations/{st.session_state.selected_conversation_id}",
            headers=get_headers(),
        )
        for message in detail["messages"]:
            with st.chat_message(message["role"]):
                st.write(message["content"])
                if message.get("citations"):
                    render_citations(message["citations"])
                if message["role"] == "assistant":
                    render_feedback(message["id"])

    question = st.chat_input("Ask something about your documents")
    if question:
        payload = {
            "question": question,
            "conversation_id": st.session_state.selected_conversation_id,
            "document_ids": selected_ids or None,
        }
        response = api_request("POST", "/chat/query", headers=get_headers(), json=payload)
        st.session_state.selected_conversation_id = response["conversation_id"]
        st.rerun()


def main():
    init_state()
    if not st.session_state.token:
        render_auth()
        return

    render_sidebar()
    left, right = st.columns([1, 2])
    with left:
        documents = render_documents()
    with right:
        render_chat(documents or [])


if __name__ == "__main__":
    main()
