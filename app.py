from flask import Flask, render_template, request, redirect, url_for, session
from utils.predict import predict_crop_util, predict_price_util
from database.models import db, User
from data.crops_data import crops_database
from data.state_data import state_data
from dotenv import load_dotenv
load_dotenv()
import joblib
import requests
import random
import os

from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)



app.config['SECRET_KEY'] = os.environ.get("SECRET_KEY", "fallback_secret")

app.config['SQLALCHEMY_DATABASE_URI'] = "sqlite:///users.db"

app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db.init_app(app)

with app.app_context():
    db.create_all()

@app.route("/")
def firstAppearance():
    
    return render_template("firstAppearance.html")



@app.route('/signup', methods=['GET','POST'])
def signup():


    
    if request.method == 'POST':

        username = request.form['username']
        email = request.form['email']
        password = request.form['password']

        existing_user = User.query.filter_by(username=username).first()

        if existing_user:
            return "Username already exists"

        hashed_password = generate_password_hash(password)

        user = User(username=username, email=email, password=hashed_password)

        db.session.add(user)
        db.session.commit()

        return redirect(url_for('login'))

    return render_template("signup.html")


@app.route('/login', methods=['GET','POST'])
def login():


    
    if request.method == 'POST':

        username = request.form['username']
        password = request.form['password']

        user = User.query.filter_by(username=username).first()

        if user and check_password_hash(user.password, password):

            session['user'] = username
            return redirect(url_for('home'))

        else:
            return "Invalid Credentials"

    return render_template("login.html")

@app.route('/logout')
def logout():

    if 'user' not in session:
        return redirect(url_for('login'))
    
    session.pop('user', None)

    return render_template("logout.html")



@app.route('/home')
def home():

    if 'user' not in session:
        return redirect(url_for('login'))
    


    return render_template("home.html")


@app.route('/about')
def about():
    if 'user' not in session:
        return redirect(url_for('login'))
    
    return render_template("about.html")



@app.route('/stateAdvisory', methods=['GET','POST'])
def stateAdvisory():

    if 'user' not in session:
        return redirect(url_for('login'))
    
    advisory = None
    state_name = None
    error = None

    if request.method == "POST":

        # Convert input to match dictionary format
        state = request.form['state'].lower().replace(" ", "_")

        advisory = state_data.get(state)

        if advisory:
            state_name = state.replace("_", " ").title()
        else:
            error = "State data not found. Please select a valid state."

    return render_template(
    "stateAdvisory.html",
    advisory=advisory,
    state_name=state_name,
    error=error,
    states=state_data.keys()
)

@app.route('/weatherInsights', methods=['GET','POST'])
def weatherInsights():

    if 'user' not in session:
        return redirect(url_for('login'))
    
    weather = None
    city = None

    API_KEY = os.environ.get("WEATHER_API_KEY")

    if request.method == "POST":

        city = request.form['city']

        url = f"https://api.openweathermap.org/data/2.5/weather?q={city}&appid={API_KEY}&units=metric"

        response = requests.get(url, timeout=5)
        data = response.json()

        if data["cod"] == 200:

            temperature = data["main"]["temp"]
            humidity = data["main"]["humidity"]
            weather_desc = data["weather"][0]["description"]

            advice = "Good weather for farming activities."

            if temperature > 35:
                advice = "High temperature. Ensure proper irrigation."

            elif humidity > 80:
                advice = "High humidity. Monitor crops for fungal diseases."

            weather = {
                "temperature": f"{temperature} °C",
                "humidity": f"{humidity} %",
                "rainfall": weather_desc,
                "advice": advice
            }

        else:
            weather = {
                "temperature":"N/A",
                "humidity":"N/A",
                "rainfall":"City not found",
                "advice":"Please enter a valid city."
            }

    return render_template(
        "weatherInsights.html",
        weather=weather,
        city=city
    )

@app.route('/marketInsights', methods=['GET','POST'])
def marketInsights():

    if 'user' not in session:
        return redirect(url_for('login'))
    
    data = None
    default_data = []
    error = None

    API_KEY = os.environ.get("MARKET_API_KEY")


    if request.method == "GET":

        default_crops = ["Wheat", "Rice", "Maize"]

        for crop in default_crops:
            try:
                url = f"https://api.data.gov.in/resource/9ef84268-d588-465a-a308-a864a43d0070?api-key={API_KEY}&format=json&filters[commodity]={crop}&limit=6"

                response = requests.get(url, timeout=5)
                result = response.json()

                records = result.get("records")

                if records:
                    default_data.append(records[0])

            except:
                continue


    if request.method == "POST":

        crop = request.form['crop'].title()
        state = request.form['state'].title()

        try:
            url = f"https://api.data.gov.in/resource/9ef84268-d588-465a-a308-a864a43d0070?api-key={API_KEY}&format=json&filters[commodity]={crop}&limit=6"

            
            response = requests.get(url, timeout=5)

            result = response.json()

            records = result.get("records")

            if records:
                data = records
            else:
                error = "No data found"

        except Exception as e:
            print("ERROR:", e)
            error = "API failed"

    return render_template(
        "marketInsights.html",
        data=data,
        default_data=default_data,
        error=error
    )
    
    


@app.route('/cropRecommendation', methods=['GET','POST'])
def cropRecommendation():

    if 'user' not in session:
        return redirect(url_for('login'))
    
    if request.method == "POST":

        N = float(request.form['N'])
        P = float(request.form['P'])
        K = float(request.form['K'])
        temperature = float(request.form['temperature'])
        humidity = float(request.form['humidity'])
        ph = float(request.form['ph'])
        rainfall = float(request.form['rainfall'])

        crop = predict_crop_util(N, P, K, temperature, humidity, ph, rainfall)

        return render_template(
            "result.html",
            crop=crop,
            N=N,
            P=P,
            K=K,
            temperature=temperature,
            humidity=humidity,
            ph=ph,
            rainfall=rainfall
        )

    return render_template("cropRecommendation.html")


@app.route('/cropsInfo', methods=['GET','POST'])
def cropsInfo():

    if 'user' not in session:
        return redirect(url_for('login'))
    
    crop_data = None
    crop_name = None

    

    if request.method == "POST":

        crop_name = request.form['crop'].strip().lower()
        
        crop_data = crops_database.get(crop_name)

    return render_template("cropsInfo.html", crop_data=crop_data, crop_name=crop_name)




@app.route('/cropPrice', methods=['GET','POST'])
def cropPrice():

    if 'user' not in session:
        return redirect(url_for('login'))
    
    prediction = None
    error = None

    API_KEY = os.environ.get("CROP_PRICE_API_KEY")

    if request.method == "POST":

        crop = request.form['crop'].title()
        month = request.form['month'].lower()

        try:
            # -------- STEP 1: GET BASE PRICE FROM API --------
            url = f"https://api.data.gov.in/resource/9ef84268-d588-465a-a308-a864a43d0070?api-key={API_KEY}&format=json&filters[commodity]={crop}&limit=5"

            response = requests.get(url, timeout=5)
            result = response.json()

            records = result.get("records")

            if not records:
                error = "No data found for this crop"
            else:
                # Take average of prices
                prices = [int(r["modal_price"]) for r in records if r.get("modal_price")]
                base_price = sum(prices) // len(prices)

            predicted_price, trend = predict_price_util(base_price, month)

            prediction = {
                    "base_price": base_price,
                    "predicted_price": predicted_price,
                    "trend": trend,
                    "advice": f"Based on current trends, {crop} prices may {trend.lower()} in coming weeks."
                }

        except Exception as e:
            print("ERROR:", e)
            error = "Prediction failed"

    return render_template(
        "cropPrice.html",
        prediction=prediction,
        error=error
    )



@app.context_processor
def inject_user():
    

    
    return dict(user=session.get('user'))









if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port , debug=True)