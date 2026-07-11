import os
import json
import numpy as np
import joblib

class FloodPredictionExplainer:
    def __init__(self, models_dir):
        self.models_dir = models_dir
        self.stats_path = os.path.join(models_dir, 'feature_stats.json')
        self.model_path = os.path.join(models_dir, 'best_model.pkl')
        self.feature_cols_path = os.path.join(models_dir, 'feature_columns.pkl')
        
        # Load pre-calculated stats
        if os.path.exists(self.stats_path):
            with open(self.stats_path, 'r') as f:
                self.stats = json.load(f)
        else:
            self.stats = {}
            
        # Load feature columns
        if os.path.exists(self.feature_cols_path):
            self.feature_cols = joblib.load(self.feature_cols_path)
        else:
            self.feature_cols = []
            
        # Load best model to get feature importances
        if os.path.exists(self.model_path):
            self.model = joblib.load(self.model_path)
            if hasattr(self.model, 'feature_importances_'):
                self.importances = dict(zip(self.feature_cols, self.model.feature_importances_))
            else:
                self.importances = {col: 0.1 for col in self.feature_cols}
        else:
            self.importances = {}

    def explain(self, input_data, prediction, probability):
        """
        Generates local explanation metrics and natural language descriptions.
        """
        contributions = {}
        explanation_details = []
        
        # We calculate contribution as:
        # (input_val - no_flood_median) / (overall_max - overall_min) * feature_importance
        for col in self.feature_cols:
            if col not in input_data or col not in self.stats:
                continue
            
            val = float(input_data[col])
            stat = self.stats[col]
            no_flood_med = stat['no_flood_median']
            flood_med = stat['flood_median']
            feat_range = stat['overall_max'] - stat['overall_min']
            if feat_range == 0:
                feat_range = 1
                
            importance = self.importances.get(col, 0.1)
            
            # Distance from safe median
            diff_from_safe = val - no_flood_med
            rel_diff = diff_from_safe / feat_range
            
            # Weighted contribution score
            score = rel_diff * importance
            contributions[col] = score
            
            # Generate descriptions
            percentage_diff = (val - no_flood_med) / no_flood_med * 100 if no_flood_med != 0 else 0
            
            # Map friendly names
            friendly_names = {
                'Temp': 'Temperature',
                'Humidity': 'Humidity',
                'Cloud Cover': 'Cloud Cover',
                'ANNUAL': 'Annual Rainfall',
                'Jan-Feb': 'Winter Rainfall (Jan-Feb)',
                'Mar-May': 'Spring Rainfall (Mar-May)',
                'Jun-Sep': 'Monsoon Rainfall (Jun-Sep)',
                'Oct-Dec': 'Post-Monsoon Rainfall (Oct-Dec)',
                'avgjune': 'Average June Rainfall',
                'sub': 'Sub-division Rainfall'
            }
            fname = friendly_names.get(col, col)
            
            if col in ['Jun-Sep', 'ANNUAL', 'avgjune', 'sub']:
                if val > no_flood_med:
                    explanation_details.append({
                        'feature': col,
                        'name': fname,
                        'value': val,
                        'baseline': no_flood_med,
                        'status': 'higher',
                        'percent': round(abs(percentage_diff), 1),
                        'text': f"{fname} is {val:.1f} mm, which is {abs(percentage_diff):.1f}% higher than the typical non-flood median of {no_flood_med:.1f} mm."
                    })
                elif val < no_flood_med:
                    explanation_details.append({
                        'feature': col,
                        'name': fname,
                        'value': val,
                        'baseline': no_flood_med,
                        'status': 'lower',
                        'percent': round(abs(percentage_diff), 1),
                        'text': f"{fname} is {val:.1f} mm, which is {abs(percentage_diff):.1f}% lower than the typical non-flood median of {no_flood_med:.1f} mm."
                    })
                else:
                    explanation_details.append({
                        'feature': col,
                        'name': fname,
                        'value': val,
                        'baseline': no_flood_med,
                        'status': 'normal',
                        'percent': 0.0,
                        'text': f"{fname} is {val:.1f} mm, matching the historical non-flood median."
                    })
            else:
                # For non-rainfall columns, show standard values
                if col == 'Temp':
                    explanation_details.append({
                        'feature': col,
                        'name': fname,
                        'value': val,
                        'baseline': no_flood_med,
                        'status': 'higher' if val > no_flood_med else ('lower' if val < no_flood_med else 'normal'),
                        'percent': 0.0,
                        'text': f"Temperature is {val:.1f}°C (historical non-flood average is {no_flood_med:.1f}°C)."
                    })
                elif col == 'Humidity':
                    explanation_details.append({
                        'feature': col,
                        'name': fname,
                        'value': val,
                        'baseline': no_flood_med,
                        'status': 'higher' if val > no_flood_med else ('lower' if val < no_flood_med else 'normal'),
                        'percent': 0.0,
                        'text': f"Relative humidity is {val:.1f}% (historical non-flood average is {no_flood_med:.1f}%)."
                    })
                elif col == 'Cloud Cover':
                    explanation_details.append({
                        'feature': col,
                        'name': fname,
                        'value': val,
                        'baseline': no_flood_med,
                        'status': 'higher' if val > no_flood_med else ('lower' if val < no_flood_med else 'normal'),
                        'percent': 0.0,
                        'text': f"Cloud cover density is {val:.1f}% (historical non-flood average is {no_flood_med:.1f}%)."
                    })

        # Sort contributions to find key drivers
        sorted_contribs = sorted(contributions.items(), key=lambda x: abs(x[1]), reverse=True)
        top_drivers = []
        for feat, score in sorted_contribs[:3]:
            # Get text for this feature
            txt = next((item['text'] for item in explanation_details if item['feature'] == feat), "")
            top_drivers.append({
                'feature': feat,
                'name': explanation_details[0]['name'] if explanation_details else feat, # temporary fallback
                'score': score,
                'text': txt
            })
            
        # Overall natural language summary
        if prediction == 1:
            summary = (
                f"The flood risk is HIGH ({probability*100:.1f}% probability) primarily driven by "
                f"elevated precipitation levels. "
            )
            monsoon_item = next((item for item in explanation_details if item['feature'] == 'Jun-Sep'), None)
            annual_item = next((item for item in explanation_details if item['feature'] == 'ANNUAL'), None)
            
            recs = [
                "Monitor local emergency broadcasts and weather advisories.",
                "Avoid traveling through low-lying waterlogged roads.",
                "Ensure drainage channels around residential areas are clear."
            ]
            if monsoon_item and monsoon_item['status'] == 'higher':
                summary += f"Specifically, the Monsoon Rainfall (Jun-Sep) of {monsoon_item['value']:.1f} mm exceeds the historical safe threshold by {monsoon_item['percent']:.1f}%."
                recs.append("Prepare emergency flood kits and elevate essential items.")
            else:
                summary += "Total annual precipitation exceeds standard thresholds."
        else:
            summary = (
                f"The flood risk is LOW ({(1-probability)*100:.1f}% safety confidence). "
                f"Meteorological values are within safe historical operating limits. "
            )
            monsoon_item = next((item for item in explanation_details if item['feature'] == 'Jun-Sep'), None)
            if monsoon_item and monsoon_item['status'] == 'lower':
                summary += f"Monsoon rainfall is {monsoon_item['percent']:.1f}% below the threshold linked with historical floods."
            recs = [
                "No immediate emergency actions required.",
                "Standard agricultural irrigation planning can proceed.",
                "Routine weather monitoring is advised."
            ]

        # Convert contributions to simple float dictionary for JS Chart
        chart_data = {k: float(v) for k, v in contributions.items()}

        return {
            'prediction': int(prediction),
            'probability': float(probability),
            'confidence_score': round(float(probability if prediction == 1 else (1 - probability)) * 100, 1),
            'risk_level': "HIGH FLOOD RISK" if prediction == 1 else "LOW FLOOD RISK",
            'summary': summary,
            'details': explanation_details,
            'chart_data': chart_data,
            'recommendations': recs
        }
