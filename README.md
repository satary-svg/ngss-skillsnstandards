# NGSS Toolkit — Streamlit App (Skills & Standards)
A ready-to-deploy Streamlit app that lets you upload NGSS CSVs, search/filter, and export. Includes a toggle for **Skills** vs **Standards** datasets.

## Run locally
```bash
pip install -r requirements.txt
streamlit run app.py
```

## Deploy (Streamlit Community Cloud)
1. Push this folder to a **new GitHub repo**.
2. Go to https://share.streamlit.io/ → **Deploy an app**.
3. Select your repo, branch, and set **Main file path** to `app.py`.
4. (Optional) Add CSVs into `/data` in your repo.
