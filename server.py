import os
import requests
from flask import Flask, request, jsonify
from flask_cors import CORS
from werkzeug.utils import secure_filename

# Load environment variables
from dotenv import load_dotenv
load_dotenv()

app = Flask(__name__)
CORS(app)

UPLOAD_FOLDER = 'uploads'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# Endpoint to get Salesforce access token
@app.route('/auth/salesforce', methods=['POST'])
def get_salesforce_token():
    try:
        data = {
            'grant_type': 'password',
            'client_id': os.getenv('SALESFORCE_CLIENT_ID'),
            'client_secret': os.getenv('SALESFORCE_CLIENT_SECRET'),
            'username': os.getenv('SALESFORCE_USERNAME'),
            'password': os.getenv('SALESFORCE_PASSWORD') + os.getenv('SALESFORCE_SECURITY_TOKEN')
        }
        response = requests.post('https://test.salesforce.com/services/oauth2/token', data=data)
        response.raise_for_status()
        return jsonify(response.json())
    except requests.exceptions.RequestException as e:
        return jsonify({'error': str(e)}), 400

# File upload endpoint
@app.route('/api/upload', methods=['POST'])
def upload_file():
    try:
        if 'file' not in request.files:
            return jsonify({'error': 'No file part'}), 400
        files = request.files.getlist('file')
        lead_id = request.form.get('leadId')
        file_paths = []
        for file in files:
            filename = secure_filename(file.filename)
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(filepath)
            file_paths.append(filepath)
        return jsonify({'message': 'Files uploaded successfully', 'files': file_paths, 'leadId': lead_id})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# Convert Lead to Opportunity
@app.route('/convert-lead', methods=['POST'])
def convert_lead():
    try:
        data = request.json
        lead_id = data.get('leadId')
        access_token = data.get('accessToken')
        instance_url = data.get('instanceUrl')
        stage_name = data.get('StageName')
        opportunity_name = data.get('opportunityName')
        do_not_create_opportunity = data.get('doNotCreateOpportunity', False)
        account_id = data.get('accountId')
        contact_id = data.get('contactId')

        headers = {'Authorization': f'Bearer {access_token}', 'Content-Type': 'application/json'}

        # Update Lead status
        patch_url = f"{instance_url}/services/data/v63.0/sobjects/Lead/{lead_id}"
        requests.patch(patch_url, json={'Status': 'Working - Contacted'}, headers=headers)

        # Convert Lead
        post_url = f"{instance_url}/services/data/v63.0/sobjects/Lead/{lead_id}/convert"
        payload = {
            'convertedStatus': stage_name,
            'opportunityName': opportunity_name,
            'doNotCreateOpportunity': do_not_create_opportunity,
            'accountId': account_id,
            'contactId': contact_id
        }
        response = requests.post(post_url, json=payload, headers=headers)
        response.raise_for_status()
        return jsonify(response.json())
    except requests.exceptions.RequestException as e:
        return jsonify({'error': str(e)}), 400

# Test Lead Conversion
@app.route('/test-convert', methods=['POST'])
def test_convert():
    try:
        lead_id = "00QAu00000OcdnJMAR"
        access_token = "your_access_token_here"
        instance_url = "https://erptechnicals--fulrdpbx.sandbox.my.salesforce.com"
        converted_status = "Qualification"

        response = requests.post(
            "http://localhost:5000/convert-lead",
            json={
                'leadId': lead_id,
                'accessToken': access_token,
                'instanceUrl': instance_url,
                'StageName': converted_status,
                'opportunityName': "Test Opportunity",
                'doNotCreateOpportunity': False,
                'accountId': None,
                'contactId': None,
            }
        )
        return jsonify(response.json())
    except requests.exceptions.RequestException as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True, port=5000)
