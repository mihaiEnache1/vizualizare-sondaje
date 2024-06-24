import json
import os
import plotly.express as px
from collections import Counter
from google.cloud import storage
import streamlit as st
import tempfile
import pandas as pd

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
        all_responses.append((blob.name, json.loads(data)))

    return all_responses

# Descarcă toate răspunsurile
responses_prefix = "responses/"
all_responses = download_all_responses(bucket_name, responses_prefix)

# Grupăm răspunsurile pe sondaje
responses_by_survey = {}
for blob_name, responses in all_responses:
    # Extragem numele sondajului din numele fișierului
    survey_name = blob_name.split('_')[1]  # Presupunem că numele sondajului este după primul underscore
    if survey_name not in responses_by_survey:
        responses_by_survey[survey_name] = []
    responses_by_survey[survey_name].append(responses)

# Funcție pentru a calcula selecțiile de imagini și a genera graficul
def calculate_and_plot_image_selections(survey_responses, survey_name):
    image_counts_existent = Counter()
    image_counts_generated = Counter()
    count_all_selected = 0
    count_none_selected = 0

    for responses in survey_responses:
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
        'Image Types': ['Existing Dataset', 'Newly Generated', 'All', 'None'],
        'Selections counter': [total_existent, total_generated, count_all_selected, count_none_selected]
    }

    # Creăm un dataframe cu pandas pentru plotly
    df = pd.DataFrame(data)

    # Generăm graficul cu plotly
    fig = px.bar(df, x='Image Types', y='Selections counter', color='Image Types',
                 title=f'Comparison in image selections for {survey_name}',
                 color_discrete_map={
                     'Existing Dataset': 'blue',
                     'Newly Generated': 'green',
                     'All': 'orange',
                     'None': 'red'
                 })

    return fig

# Afișăm graficele pentru fiecare sondaj
st.title("User study results")

for survey_name, survey_responses in responses_by_survey.items():
    fig = calculate_and_plot_image_selections(survey_responses, survey_name)
    st.plotly_chart(fig)

# Afișăm graficul cumulativ pentru toate sondajele
all_responses_combined = [responses for survey_responses in responses_by_survey.values() for responses in survey_responses]
fig_cumulative = calculate_and_plot_image_selections(all_responses_combined, "all surveys combined")
st.plotly_chart(fig_cumulative)
