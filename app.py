import streamlit as st
import time
import requests
import numpy as np
from PIL import Image
from google.cloud import bigquery
import datetime
import plotly.express as px
import pandas as pd
import json

# Initialization
if "user_ID" not in st.session_state:
    st.session_state['user_ID'] = 1


#Function
def calc_objectif(weigth,height,age,genre:str):
    """Calculate the portion of macronutriment based on height,weight,age and genre \n
    Return protein,fat,carbs,obj"""
    if genre == "M":
        calories = 88.362 + 13.397*weigth + 4.799*height - 5.677*age
        protein = 1.7*weigth
        fat = (calories*0.2)/9
        carbs = ((protein*4)+(fat*9))/4
        obj = calories *1.2
    else:
        calories = 447.593 + 9.247*weigth + 3.098*height - 4.330*age
        protein = 1.7*weigth
        fat = (calories*0.2)/9
        carbs = ((protein*4)+(fat*9))/4
        obj = calories *1.2
    return protein,fat,carbs,obj

def run_query(query):
    query_job = client.query(query)
    rows_raw = query_job.result()
    # Convert to list of dicts. Required for st.cache_data to hash the return value.
    rows = [dict(row) for row in rows_raw]
    return rows

def new_ID(ID, height, weigth, age, genre):

    query =   f"INSERT INTO `foode-376420.foodE.ID_info` (UserID, Height, Weigth, Age, Genre) VALUES ({ID}, {height}, {weigth}, {age}, '{genre}')"
    rows = run_query(query)
    return rows

def exist_ID(ID):
    query = f"SELECT EXISTS( SELECT * FROM `foode-376420.foodE.ID_info` WHERE UserID={ID} )"
    rows = run_query(query)
    return rows

def ID_read(ID):
    query = f"SELECT * FROM `foode-376420.foodE.ID_info` WHERE UserID = {ID}"
    rows = run_query(query)
    return rows

#Instanciate client for bigquery
client = bigquery.Client()


# Create a sidebar with navigation links
st.sidebar.title("Navigation")

page = st.sidebar.radio("Go to", ["Personal information",  "Camera", "Upload", "Journal"])


# Use the page variable to determine which page to display
if page == "Personal information":
    st.title("Personal information")

    with st.form(key='my_data_1'):
        t1, _, _ = st.columns(3)
        with t1 :
            user_ID = st.number_input(label='Enter your User ID please : ', value = 1)


        submit_button = st.form_submit_button(label='Submit')
        if submit_button:
            st.session_state.user_ID = user_ID
        # Verifier si l'ID Exist
        exist_id = exist_ID(user_ID)[0]['f0_']


    #Logic for existing User
    if exist_id :
        id_read = ID_read(user_ID)[0]
        st.write("<center>Welcome</center>",unsafe_allow_html=True)
        st.write(f"<center>L'ID numéro {user_ID} est bien present dans notre base des données</center>"\
                ,unsafe_allow_html=True)

        #Get objectives data
        query = f"SELECT * from foode-376420.foodE.objectif WHERE UserID = {user_ID}"
        query_job = client.query(query)
        rows_raw = query_job.result()
        rows = [dict(row) for row in rows_raw]
        protein = rows[0]["Protein"]
        carbs = rows[0]["Carbs"]
        fat = rows[0]["Fat"]
        calories = rows[0]["Calories"]

        #Daily objectives display
        st.write("<center style = 'font-size:35px;'>Daily Objectives</center>",unsafe_allow_html=True)
        c1,c2 = st.columns(2)

        #Display pie chart for macronutriment
        data = pd.DataFrame({
            'Macronutrient': ['Protein', 'Carbs', 'Fat'],
            'Grams': [protein,carbs, fat]
})
        pie = px.pie(data,values='Grams',color_discrete_sequence=["#167d09","#2e76e8","#ad0a0a"],hole=0.4,\
            labels=["protein","carbs","fat"],names=["protein","carbs","fat"])
        c2.plotly_chart(pie,use_container_width=500)

        #Display frame of objectives

        c1.markdown(f"""
        <div style="position: absolute; top: 150px; left: 5px;">
        🔥 {calories} calories <br>
        🥚 {protein}g proteins <br>
        🍞 {carbs}g carbs <br>
        🥑 {fat}g fat</div>
        """, unsafe_allow_html=True)
        #st.write(respons

        #Form to change weight
        form = st.form(key='my_data')
        c1,_ = form.columns(2)
        weigth = c1.slider(label='Change your weigth (kg) : ', min_value=40, max_value=150)
        submit_button = c1.form_submit_button(label='Submit')

        #Update Bigquery tables with new weight
        if submit_button:
            #Update weight in personnal info
            weight_query = f"UPDATE `foode-376420.foodE.ID_info` SET Weigth = {weigth} WHERE UserID={user_ID}"
            query_job = client.query(weight_query)
            rows_raw = query_job.result()

            #Change objective
            protein,fat,carbs,obj = calc_objectif(weigth,id_read["Height"],id_read["Age"],id_read["Genre"])
            objectif_query= f"UPDATE foode-376420.foodE.objectif\
                SET Protein = {round(protein,1)},Carbs = {round(carbs,1)}\
                    ,Fat = {round(fat,1)},Calories = {round(obj,1)}\
                WHERE UserID = {user_ID}"
            query_job = client.query(objectif_query)
            query_job.result()

            #Reload page, to show pie chart with new value
            st.experimental_rerun()


    #Logic to write a new ID in database
    else:
        st.write(f"L'user ID n'existe pas dans notre base. S'il vous plaît creez un nouveau utilisateur en renseignant les informations ci-dessous:")

        with st.form(key='my_data_2'):

            c1, c2 = st.columns(2)
            with c1:
                genre = st.selectbox("Genre : ", ["M", "F"])
                height = st.slider(label='Enter your height (cm) please : ', min_value=100, max_value=220)
            with c2:
                age = st.number_input(label='Age : ', value = 15)
                weigth = st.slider(label='Enter your weigth (kg) please : ', min_value=40, max_value=150)

            submit_button_2 = st.form_submit_button(label='Submit')

        if submit_button_2 :
            new_ID(user_ID, height, weigth, age, genre)

            #Calcul d'objectif
            protein,fat,carbs,obj = calc_objectif(weigth,height,age,genre)

            #Pushing queries to BQ
            obj_update =   f"INSERT INTO `foode-376420.foodE.objectif` (UserID, Protein, Carbs, Fat, Calories)\
                VALUES ({round(user_ID,1)}, {round(protein,1)}, {round(carbs,1)}, {round(fat,1)}, {round(obj,1)})"
            query_job = client.query(obj_update)
            rows_raw = query_job.result()

            #Reload page to show pie chart after creating the new user
            st.experimental_rerun()


        # tester le fonctionnement de value
        # test = f'Heigth : {height}, weigth = {weigth}, user = {user_ID}'
        # st.write(test)


if page == "Camera":
    st.title("Camera")
    img_file_buffer = st.camera_input("Take a picture")

    with st.spinner("Wait for it..."):
        time.sleep(2.5)
        if img_file_buffer:
            # Change image to the correct size
            img = Image.open(img_file_buffer)
            img_height = 260
            img_width = 260
        # st.write(img_width)
            img = img.resize((img_height,img_width))
            #st.write(type(img))

            # Transform img to np.array
            img_array = np.array(img)
            #st.write(img_array.shape)

            # Make a json with a list
            user_ID =  st.session_state.user_ID
            jayson = {"img": img_array.tolist(), "userid" : int(user_ID)}

            # Post request to API
            headers = {'Content-Type': 'application/json'}
            #url = "https://api-xdmhayaf3a-nw.a.run.app/predict"
            url = "http://localhost:8000/predict"
            response = requests.post(f"{url}", headers = headers, json=jayson)

            if response.status_code == 200:
                st.balloons()
                response_list = json.loads(response.content.decode('utf-8'))
                body_list = [item['body'] for item in response_list]

                # st.write(f"Per 100g your {body_list[0]} meal contains: {body_list[1]} calories, {body_list[2]} carbs,\
                #    {body_list[3]} fat, {body_list[4]} proteins")

                st.markdown(f"""
                                ## 🍽️ : {body_list[0]}

                                #### **Per serving** :

                                🔥 {body_list[1]} calories

                                🥚 {body_list[4]}g proteins

                                🍞 {body_list[2]}g carbs

                                🥑 {body_list[3]}g fat

                            """)
                #st.write(response.content)
            else:
                st.markdown("**Oops**, something went wrong 😓 Please try again.")
                print(response.status_code, response.content)


if page == "Upload":
    img_file_buffer = st.file_uploader("Food image to predict your Calories", type=None, accept_multiple_files=False, key=None, help=None, on_change=None,disabled=False, label_visibility="visible")
    if img_file_buffer:
        st.image(img_file_buffer)
        # Change image to the correct size
        img = Image.open(img_file_buffer)
        img_height = 260
        img_width = 260
    # st.write(img_width)
        img = img.resize((img_height,img_width))
        #st.write(type(img))

        # Transform img to np.array
        img_array = np.array(img)
        #st.write(img_array.shape)

        user_ID =  st.session_state.user_ID
        # Make a json with a list
        jayson = {"img": img_array.tolist(), "userid" : int(user_ID)}

        # Post request to API
        headers = {'Content-Type': 'application/json'}
        #url = "https://api-xdmhayaf3a-nw.a.run.app/predict"
        url = "http://localhost:8000/predict"
        response = requests.post(f"{url}", headers = headers, json=jayson)

        if response.status_code == 200:
            st.balloons()
            response_list = json.loads(response.content.decode('utf-8'))
            body_list = [item['body'] for item in response_list]

            # st.write(f"Per 100g your {body_list[0]} meal contains: {body_list[1]} calories, {body_list[2]} carbs,\
            #    {body_list[3]} fat, {body_list[4]} proteins")

            st.markdown(f"""
                            ## 🍽️ : {body_list[0]}

                            #### **Per serving** :

                            🔥 {body_list[1]} calories

                            🥚 {body_list[4]}g proteins

                            🍞 {body_list[2]}g carbs

                            🥑 {body_list[3]}g fat

                        """)
            #st.write(response.content)
        else:
            st.markdown("**Oops**, something went wrong 😓 Please try again.")
            print(response.status_code, response.content)


if page == "Journal":

    # select = st.sidebar.selectbox('Select a State',["France"])

    # if select:

    #     progress_text = "Proteine"
    #     my_bar = st.progress(70, text=progress_text)

    d = st.date_input(
        "Date",
        datetime.date.today())

    client = bigquery.Client()

    # DAILY OBJ
    #Objectives request
    user_ID = st.session_state.user_ID
    query = f"SELECT * from foode-376420.foodE.objectif WHERE UserID = {user_ID}"
    query_job = client.query(query)
    rows_raw = query_job.result()
    rows = [dict(row) for row in rows_raw]
    protein = rows[0]["Protein"]
    carbs = rows[0]["Carbs"]
    fat = rows[0]["Fat"]
    calories = rows[0]["Calories"]

    #Daily request
    query = f"""SELECT SUM(Protein) AS Protein, SUM(Calories) as Calories , SUM(Carbs) AS Carbs , SUM(Fat) AS Fat,
        FROM `foode-376420.foodE.macro`
        WHERE UserID = {user_ID} AND Date = '{d}'"""
    query_job = client.query(query)
    rows_raw = query_job.result()
    rows = [dict(row) for row in rows_raw]
    d_prot = int(rows[0]["Protein"])
    if d_prot > 100: d_prot=100
    d_cal = int(rows[0]["Calories"])
    if d_cal > 100: d_cal=100
    d_carbs = int(rows[0]["Carbs"])
    if d_carbs > 100: d_carbs=100
    d_fat = int(rows[0]["Fat"])
    if d_fat > 100: d_fat=100

    #Daily graph
    #Progress bar

    c1,c2 = st.columns(2)
    c1.header("Daily")
    c1.progress(d_cal, text="🔥 Calories")
    c1.progress(d_prot, text="🥚 Protein")
    c1.progress(d_carbs, text="🍞 Carbs")
    c1.progress(d_fat, text="🥑 Fat")

    st.markdown(
    """
    <style>
    .stProgress > div {
        margin-top: 10px;
        padding-right: 75px;
    }
    </style>
    """,
    unsafe_allow_html=True
)

    #Pie chart
    data = pd.DataFrame({
    'Macronutrient': ['Protein', 'Carbs', 'Fat'],
    'Grams': [d_prot,d_carbs, d_fat]})
    pie = px.pie(data,values='Grams',color_discrete_sequence=["#167d09","#2e76e8","#ad0a0a"],\
    labels=["protein","carbs","fat"],names=["protein","carbs","fat"])
    c2.plotly_chart(pie,use_container_width=500)

    # WEEKLY EVOLUTION
    st.header("Weekly")
    cal_sevendays = f"""
        SELECT Date, SUM(Calories) AS Calories
        FROM `foode-376420.foodE.macro`
        WHERE UserID = {user_ID} AND Date BETWEEN DATE_SUB('{d}', INTERVAL 7 DAY) AND '{d}'
        GROUP BY Date
     """


    st.write("Objectif calorique sur les 7 derniers jours")

    st.area_chart(data = client.query(cal_sevendays).to_dataframe(), x='Date') # AJOUTER UNE LIGNE OBJ

    nutri_sevendays = f"""
        SELECT Date, SUM(Protein)*20/100 AS Protein , SUM(Carbs)/100 AS Carbs , SUM(Fat)*20/100 AS Fat
        FROM `foode-376420.foodE.macro`
        WHERE UserID = {user_ID} AND Date BETWEEN DATE_SUB('{d}', INTERVAL 7 DAY) AND '{d}'
        GROUP BY Date
     """

    st.write("Objectif nutritionnel sur les 7 derniers jours")

    st.line_chart(data = client.query(nutri_sevendays).to_dataframe(), x='Date') # AJOUTER UNE LIGNE OBJ

    # https://docs.streamlit.io/library/api-reference/charts/st.altair_chart ?

    # DATABASE
    st.header("Database")
    query = f"""
        SELECT *
        FROM `foode-376420.foodE.macro`
        WHERE Date = '{d}' AND UserID = {user_ID}
     """
    results = client.query(query)
    results = results.to_dataframe()
    st.write(results)

    ## AAGRID TO EDIT? https://streamlit-aggrid.readthedocs.io/en/docs/AgGrid.html
