import json
import os
import plotly.express as px
from collections import Counter
from google.cloud import storage
import streamlit as st
import tempfile

# Accesarea variabilei de mediu
credentials_content = st.secrets['GOOGLE_APPLICATION_CREDENTIALS_CONTENT']

# Crearea unui fișier temporar pentru cheile de autentificare
with tempfile.NamedTemporaryFile(delete=False, suffix=".json") as temp_file:
    temp_file.write(credentials_content.encode())
    temp_file_name = temp_file.name

# Initializare
os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = temp_file_name

storage_client = storage.Client()
bucket_name = 'sondaj1_bucket'
bucket = storage_client.bucket(bucket_name)

# Funcție pentru a descărca toate fișierele JSON dintr-un director din Google Cloud Storage
def download_all_responses(bucket_name, prefix):
    bucket = storage_client.bucket(bucket_name)
    blobs = bucket.list_blobs(prefix=prefix)

    all_responses = []
    for blob in blobs:
        data = blob.download_as_text()
        all_responses.append(json.loads(data))

    return all_responses

# Descarcă toate răspunsurile
responses_prefix = "responses/"
all_responses = download_all_responses(bucket_name, responses_prefix)

# Analizează răspunsurile
image_counts_existent = Counter()
image_counts_generated = Counter()
count_all_selected = 0
count_none_selected = 0

for responses in all_responses:
    for metafora, images in responses.items():
        if not images:
            count_none_selected += 1
        elif any("prev" in img for img in images) and any("prev" not in img for img in images):
            count_all_selected += 1
        else:
            for image_url in images:
                if "prev" in image_url:
                    image_counts_existent[image_url] += 1
                else:
                    image_counts_generated[image_url] += 1

# Calculăm totalul selecțiilor pentru fiecare categorie
total_existent = sum(image_counts_existent.values())
total_generated = sum(image_counts_generated.values())

# Pregătim datele pentru plotly
data = {
    'Tipul de Imagini': ['Set Existent', 'Set Nou', 'Toate', 'Niciuna'],
    'Numărul de selecții': [total_existent, total_generated, count_all_selected, count_none_selected]
}

# Creăm un dataframe cu pandas pentru plotly
import pandas as pd
df = pd.DataFrame(data)

# Generăm graficul cu plotly
fig = px.bar(df, x='Tipul de Imagini', y='Numărul de selecții', color='Tipul de Imagini',
             title='Compararea selecțiilor imaginilor',
             color_discrete_map={
                 'Set Existent': 'blue',
                 'Set Nou': 'green',
                 'Toate': 'orange',
                 'Niciuna': 'red'
             })

# Afișăm graficul în Streamlit
st.title("Rezultatele sondajului")
st.plotly_chart(fig)
