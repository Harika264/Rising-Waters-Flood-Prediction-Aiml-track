import os
import logging
import joblib
import pandas as pd
from flask import Flask, render_template, request, redirect, url_for, flash

# Configure logger
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Initialize Flask App
app = Flask(__name__)
app.secret_key = os.urandom(24) # Needed for flash messages

# Define paths
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
MODELS_DIR = os.path.join(BASE_DIR, "models")

# Load model, scaler and features
model_path = os.path.join(MODELS_DIR, "best_model.pkl")
scaler_path = os.path.join(MODELS_DIR, "scaler.pkl")
features_path = os.path.join(MODELS_DIR, "feature_columns.pkl")

# Initialize models globally
model = None
scaler = None
feature_cols = []

try:
    if os.path.exists(model_path) and os.path.exists(scaler_path) and os.path.exists(features_path):
        model = joblib.load(model_path)
        scaler = joblib.load(scaler_path)
        feature_cols = joblib.load(features_path)
        logger.info("Successfully loaded serialized model, scaler, and features list.")
    else:
        logger.warning("Serialized model files not found in models/ directory. Run model training first!")
except Exception as e:
    logger.error(f"Error loading model files: {e}")

# Import explanation utility
try:
    from utils.explainers import FloodPredictionExplainer
    explainer = FloodPredictionExplainer(MODELS_DIR)
except Exception as e:
    logger.error(f"Error importing or initializing FloodPredictionExplainer: {e}")
    explainer = None


@app.route('/')
def home():
    """Renders the dashboard and project details page."""
    return render_template('home.html', active_page='home')


@app.route('/predict')
def predict():
    """Renders the meteorological parameter input form."""
    return render_template('predict.html', active_page='predict')


@app.route('/predict_logic', methods=['POST'])
def predict_logic():
    """Handles parsing, validation, prediction, and explanations."""
    if not model or not scaler or not feature_cols:
        flash("Model system is currently offline. Please contact the administrator.", "danger")
        return redirect(url_for('predict'))
        
    try:
        # 1. Parse and validate form inputs
        input_data = {}
        errors = []
        
        # We parse according to feature columns
        for col in feature_cols:
            val_str = request.form.get(col)
            if val_str is None or val_str.strip() == "":
                errors.append(f"Missing value for {col}.")
                continue
                
            try:
                # Parse as float or int depending on column
                if col in ['Temp', 'Humidity', 'Cloud Cover']:
                    input_data[col] = int(float(val_str))
                else:
                    input_data[col] = float(val_str)
            except ValueError:
                errors.append(f"Value for {col} must be a valid number.")
                
        # Non-negative validation for rainfall
        for col in feature_cols:
            if col not in ['Temp', 'Humidity', 'Cloud Cover'] and col in input_data:
                if input_data[col] < 0:
                    errors.append(f"{col} rainfall cannot be negative.")
                    
        # Return form if validation fails
        if errors:
            for err in errors:
                flash(err, "danger")
            return redirect(url_for('predict'))

        # 2. Run prediction pipeline
        # Order columns exactly as expected by the scaler and model
        df_input = pd.DataFrame([input_data])[feature_cols]
        
        # Scale inputs
        scaled_input = scaler.transform(df_input)
        
        # Predict class and probability
        prediction = model.predict(scaled_input)[0]
        probabilities = model.predict_proba(scaled_input)[0]
        
        # Flood probability (Class 1)
        prob_flood = probabilities[1]
        
        # 3. Generate explanations
        if explainer:
            explanation = explainer.explain(input_data, prediction, prob_flood)
        else:
            explanation = {
                'prediction': int(prediction),
                'probability': float(prob_flood),
                'confidence_score': round(float(prob_flood if prediction == 1 else (1 - prob_flood)) * 100, 1),
                'risk_level': "HIGH FLOOD RISK" if prediction == 1 else "LOW FLOOD RISK",
                'summary': "Detailed explanations are currently unavailable.",
                'details': [],
                'chart_data': {},
                'recommendations': []
            }
            
        logger.info(f"Prediction made -> Status: {explanation['risk_level']}, Confidence: {explanation['confidence_score']}%")
        return render_template('result.html', explanation=explanation, active_page='predict')

    except Exception as e:
        logger.error(f"Error occurred during prediction processing: {e}")
        flash(f"An unexpected error occurred: {str(e)}", "danger")
        return redirect(url_for('predict'))


if __name__ == '__main__':
    # Bind to PORT environment variable for IBM Cloud compatibility
    port = int(os.environ.get('PORT', 8080))
    # Host must be 0.0.0.0 to be visible on container platforms
    app.run(host='0.0.0.0', port=port, debug=True)
