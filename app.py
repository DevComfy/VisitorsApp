# app.py
import os
from flask import Flask, render_template, request, redirect, url_for, jsonify, session, send_from_directory
import firebase_admin
from firebase_admin import credentials, firestore
import uuid
import smtplib
import ssl
from email.message import EmailMessage
from werkzeug.utils import secure_filename
from werkzeug.security import generate_password_hash, check_password_hash  # For HSO password hashing (basic for demo)
from functools import wraps
import datetime
import random  # Import random for generating 5-digit code

app = Flask(__name__)

# --- Configuration ---
# IMPORTANT: For production, store this securely (e.g., environment variables)
# Using os.getenv for environment variables is highly recommended for production
app.config['SECRET_KEY'] = os.getenv('FLASK_SECRET_KEY', 'a_very_secret_key_for_flask_sessions')  # Change this!
EMAIL_USER = os.getenv('EMAIL_USER', "no-reply@hcaircon.com")  # Your sender email
EMAIL_PASSWORD = os.getenv('EMAIL_PASSWORD', "V@851900510655av")  # Your email password/app password
# SMTP details for sending emails
SMTP_SERVER = os.getenv('SMTP_SERVER', "smtp-mail.outlook.com")
SMTP_PORT = int(os.getenv('SMTP_PORT', 587))

# Configure upload folder for photos and documents
UPLOAD_FOLDER = 'uploads'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)  # Create the uploads directory if it doesn't exist
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# Allowed extensions for documents uploaded by HSO
ALLOWED_DOC_EXTENSIONS = {'pdf', 'png', 'jpg', 'jpeg', 'doc', 'docx', 'xlsx', 'xls'}

# --- Firebase Initialization ---
try:
    # Use environment variable for service account path or direct file if local
    FIREBASE_SERVICE_ACCOUNT_PATH = os.getenv('FIREBASE_SERVICE_ACCOUNT_PATH', "visitors-fdf8c-fea77db60679.json")
    if os.path.exists(FIREBASE_SERVICE_ACCOUNT_PATH):
        cred = credentials.Certificate(FIREBASE_SERVICE_ACCOUNT_PATH)
        firebase_admin.initialize_app(cred)
        db = firestore.client()
        print("Firebase initialized successfully.")
    else:
        print(f"Error: Firebase service account key not found at {FIREBASE_SERVICE_ACCOUNT_PATH}")
        db = None  # Set db to None if initialization fails
except Exception as e:
    print(f"Error initializing Firebase: {e}")
    db = None  # Set db to None if initialization fails

# Global app ID for Firestore path consistency with Canvas environment
APP_ID = "default-app-id"  # You can make this dynamic if needed

# NDA Content (remains the same)
NDA_CONTENT = """
CONFIDENTIALITY AND NON-DISCLOSURE AGREEMENT

This Non-Disclosure Agreement ("Agreement") is entered into between HC Air Conditioning ("Company") and the undersigned visitor ("Visitor") for the purpose of preventing the unauthorized disclosure of Confidential Information as defined below.

1. Definition of Confidential Information:
For purposes of this Agreement, "Confidential Information" shall include all information or material that has or could have commercial value or other utility in the business in which Company is engaged. This includes but is not limited to:

Technical data, trade secrets, know-how, research, product plans
Customer lists, supplier information, pricing information
Business processes, marketing strategies, financial information
Any other proprietary information disclosed during the visit
2. Non-disclosure and Non-use Obligations:
Visitor agrees to:

Hold all Confidential Information in strict confidence
Not disclose Confidential Information to any third parties
Not use Confidential Information for any purpose other than the intended visit
Take reasonable precautions to protect the confidentiality of such information
3. Duration:
This Agreement shall remain in effect for a period of five (5) years from the date of signing, or until the information becomes publicly available through no breach of this Agreement.

4. Photography and Recording:
Visitor agrees not to photograph, record, or otherwise document any part of the Company's premises, equipment, or processes without explicit written permission.

By accepting this agreement, you acknowledge that you have read, understood, and agree to be bound by the terms of this Non-Disclosure Agreement.
"""

# --- Firestore Collections ---
HSO_USERS_COLLECTION = db.collection(f'artifacts/{APP_ID}/hso_users')
CONTRACTOR_PRE_APPROVALS_COLLECTION = db.collection(f'artifacts/{APP_ID}/contractor_pre_approvals')


# --- Utility Functions ---
def allowed_file(filename):
    return '.' in filename and \
        filename.rsplit('.', 1)[1].lower() in ALLOWED_DOC_EXTENSIONS


def _send_email(receiver_email, subject, body):
    """Helper function to send emails."""
    sender_email = EMAIL_USER
    password = EMAIL_PASSWORD

    msg = EmailMessage()
    msg['From'] = sender_email
    msg['To'] = receiver_email
    msg['Subject'] = subject
    msg.set_content(body)

    context = ssl.create_default_context()
    print(f"Attempting to send email to {receiver_email} from {sender_email}...")
    try:
        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
            server.starttls(context=context)
            server.login(sender_email, password)
            server.send_message(msg)
        print(f"Email sent successfully to {receiver_email}")
        return True
    except smtplib.SMTPAuthenticationError as e:
        print(f"SMTP Authentication Error: Check username and password for {sender_email}. Error: {e}")
        return False
    except smtplib.SMTPException as e:
        print(f"SMTP Error occurred while sending email to {receiver_email}: {e}")
        return False
    except Exception as e:
        print(f"An unexpected error occurred while sending email to {receiver_email}: {e}")
        return False


def send_email_to_visitor(email, visitor_data):
    """Sends an email to the visitor with registration details."""
    subject = "HC Air Conditioning - Your Visit Registration Confirmation"
    body = f"""Dear {visitor_data['firstName']},

Thank you for registering your visit to HC Air Conditioning.

Here are your registration details:
First Name: {visitor_data['firstName']}
Last Name: {visitor_data['lastName']}
Company: {visitor_data['company']}
Reason for Visit: {visitor_data['reasonForVisit']}
Person Visiting: {visitor_data['personVisiting']}
Email Address: {visitor_data['emailAddress']}

"""
    if visitor_data.get('needsWifi'):
        body += """
Guest Wi-Fi Access:
Network Name (SSID): HC Guest
Password: Welcome2HC
Voucher Code: 78909-13788

Instructions:
1. Connect to "HC Guest" network
2. Enter the voucher code when prompted
"""
    body += """
We look forward to your visit.

Best regards,
HC Air Conditioning Team
"""
    _send_email(email, subject, body)


def send_email_to_departments(visitor_type, visitor_data):
    """Sends emails to relevant departments about a new visitor."""
    department_emails = {
        'Factory Visitor': 'Tshidi.motebs@gmail.com',
        'Office Visitor': 'comfort.motebejane@hcaircon.com',
    }
    recipient = department_emails.get(visitor_type)

    if recipient:
        subject = f"New {visitor_type} Registration: {visitor_data['firstName']} {visitor_data['lastName']}"
        body = f"""A new {visitor_type} has registered:

Name: {visitor_data['firstName']} {visitor_data['lastName']}
Company: {visitor_data['company']}
Reason for Visit: {visitor_data['reasonForVisit']}
Person Visiting: {visitor_data['personVisiting']}
Email: {visitor_data['emailAddress']}
Photo Provided: {'Yes' if visitor_data.get('selfiePhotoPath') else 'No'}
ID Photo Provided: {'Yes' if visitor_data.get('idPicturePath') else 'No'}
Wi-Fi Needed: {'Yes' if visitor_data.get('needsWifi') else 'No'}

Please review the details in the visitor management system.
"""
        _send_email(recipient, subject, body)


# --- Authentication Decorator ---
def hso_login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'hso_user_id' not in session:
            return redirect(url_for('hso_login'))
        return f(*args, **kwargs)

    return decorated_function


# --- HSO User Management (for initial setup) ---
def create_initial_hso_user():
    """Creates a default HSO user if one doesn't exist."""
    user_ref = HSO_USERS_COLLECTION.document('hso_admin')
    user_doc = user_ref.get()

    if not user_doc.exists:
        hashed_password = generate_password_hash("admin_password")  # IMPORTANT: CHANGE THIS IN PRODUCTION!
        user_ref.set({
            'username': 'hso_admin',
            'password': hashed_password,
            'role': 'hso'
        })
        print("Default HSO user 'hso_admin' created with password 'admin_password'. CHANGE THIS IN PRODUCTION!")
    else:
        print("HSO user 'hso_admin' already exists.")


with app.app_context():
    if db:  # Only try to create if Firebase initialized successfully
        create_initial_hso_user()


# --- Routes for HSO Dashboard ---

@app.route('/hso/login', methods=['GET', 'POST'])
def hso_login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        user_query = HSO_USERS_COLLECTION.where('username', '==', username).limit(1).get()
        user_doc = None
        for doc in user_query:
            user_doc = doc
            break

        if user_doc and check_password_hash(user_doc.to_dict()['password'], password):
            session['hso_user_id'] = user_doc.id
            session['hso_username'] = user_doc.to_dict()['username']
            session['hso_user_role'] = user_doc.to_dict()['role']
            return redirect(url_for('hso_dashboard'))
        else:
            return render_template('hso_dashboard.html', login_error="Invalid credentials. Please try again.",
                                   login_page=True)
    return render_template('hso_dashboard.html', login_page=True)


@app.route('/hso/logout')
def hso_logout():
    session.pop('hso_user_id', None)
    session.pop('hso_username', None)
    session.pop('hso_user_role', None)
    return redirect(url_for('hso_login'))


@app.route('/hso/dashboard')
@hso_login_required
def hso_dashboard():
    submissions_ref = CONTRACTOR_PRE_APPROVALS_COLLECTION.order_by('created_at', direction=firestore.Query.DESCENDING)
    submissions = [doc.to_dict() for doc in submissions_ref.stream()]
    for sub in submissions:
        sub['id'] = sub.pop('firebase_id_field_name', None)  # Use actual Firestore ID
        # Convert Firestore Timestamp to string for display
        if 'created_at' in sub and hasattr(sub['created_at'], 'isoformat'):
            sub['created_at'] = sub['created_at'].isoformat()
        if 'updated_at' in sub and hasattr(sub['updated_at'], 'isoformat'):
            sub['updated_at'] = sub['updated_at'].isoformat()

    return render_template('hso_dashboard.html', submissions=submissions, login_page=False)


@app.route('/hso/upload_docs', methods=['POST'])
@hso_login_required
def hso_upload_docs():
    if db is None:
        return jsonify({"success": False, "message": "Database not initialized."}), 500

    hso_id = session.get('hso_user_id')
    company_name = request.form.get('company_name')
    contractor_contact_name = request.form.get('contractor_contact_name')
    contractor_email = request.form.get('contractor_email')
    project_reason_for_visit = request.form.get('project_reason_for_visit')
    expected_arrival_date = request.form.get('expected_arrival_date')

    # List of expected document types from the form
    document_fields = [
        'coid_letter', 'risk_assessments', 'worker_certificates',
        'material_safety_data_sheets', 'ppe_records', 'medical_certificates',
        'standard_operating_procedures', 'id_copies', 'legal_appointments',
        'miscellaneous_docs'  # For any other general documents
    ]

    # Validate core contractor details
    if not all(
            [company_name, contractor_contact_name, contractor_email, project_reason_for_visit, expected_arrival_date]):
        return jsonify({"success": False, "message": "Missing required contractor details"}), 400

    # Check if at least one file was uploaded
    any_file_uploaded = False
    for field in document_fields:
        if field in request.files and request.files[field].filename != '':
            any_file_uploaded = True
            break

    if not any_file_uploaded:
        return jsonify({"success": False, "message": "At least one document must be uploaded."}), 400

    try:
        # Generate a unique 5-digit numeric code
        unique_code = str(random.randint(10000, 99999))

        # Check if the generated code already exists (unlikely for 5 digits but good practice)
        # This will be very rare for 5-digit codes, but good practice for collision avoidance.
        # For a truly robust system, consider a loop to regenerate if a collision occurs,
        # or rely on Firestore's unique document IDs more heavily.
        existing_code_query = CONTRACTOR_PRE_APPROVALS_COLLECTION.where('unique_pre_approval_code', '==',
                                                                        unique_code).limit(1).get()
        if len(list(existing_code_query)) > 0:
            # If collision, try generating another code (simple retry, could be a loop)
            unique_code = str(random.randint(10000, 99999))

        pre_approval_doc_ref = CONTRACTOR_PRE_APPROVALS_COLLECTION.document()  # Auto-generated ID

        pre_approval_data = {
            'company_name': company_name,
            'contractor_contact_name': contractor_contact_name,
            'contractor_email': contractor_email,
            'project_reason_for_visit': project_reason_for_visit,
            'expected_arrival_date': expected_arrival_date,
            'hso_reviewer_id': hso_id,
            'submission_status': 'Pending Review',
            'unique_pre_approval_code': unique_code,
            'created_at': firestore.SERVER_TIMESTAMP,
            'updated_at': firestore.SERVER_TIMESTAMP,
            'firebase_id_field_name': pre_approval_doc_ref.id  # Store Firestore ID for easy retrieval
        }
        pre_approval_doc_ref.set(pre_approval_data)

        # Create a subcollection for documents within this pre-approval
        documents_subcollection_ref = pre_approval_doc_ref.collection('contractor_documents')

        for field_name in document_fields:
            if field_name in request.files:
                file = request.files[field_name]
                if file and allowed_file(file.filename):
                    filename = secure_filename(
                        f"{pre_approval_doc_ref.id}_{field_name}_{str(uuid.uuid4())}_{file.filename}")
                    filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                    file.save(filepath)

                    doc_data = {
                        "document_type": field_name.replace('_', ' ').title(),  # Make it readable, e.g., 'Coid Letter'
                        "file_path": filepath,  # Local path on server
                        "file_url": url_for('uploaded_file', filename=filename, _external=True),
                        # Public URL for HSO dashboard
                        "original_file_name": file.filename,
                        "uploaded_by_hso_id": hso_id,
                        "uploaded_at": firestore.SERVER_TIMESTAMP
                    }
                    documents_subcollection_ref.add(doc_data)
                elif file.filename != '':  # If file was present but not allowed
                    print(f"Skipped invalid file for {field_name}: {file.filename}")

        return jsonify({"success": True, "message": "Contractor documents uploaded for review.",
                        "pre_approval_id": pre_approval_doc_ref.id}), 201

    except Exception as e:
        print(f"Error uploading documents: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({"success": False, "message": f"Error uploading documents: {e}"}), 500


@app.route('/hso/pre-approvals/<string:pre_approval_firestore_id>')
@hso_login_required
def hso_view_submission(pre_approval_firestore_id):
    if db is None:
        return jsonify({"success": False, "message": "Database not initialized."}), 500

    submission_doc = CONTRACTOR_PRE_APPROVALS_COLLECTION.document(pre_approval_firestore_id).get()

    if not submission_doc.exists:
        return jsonify({"message": "Submission not found"}), 404

    submission_data = submission_doc.to_dict()
    submission_data['id'] = submission_doc.id  # Add the Firestore document ID to the data

    documents_ref = CONTRACTOR_PRE_APPROVALS_COLLECTION.document(pre_approval_firestore_id).collection(
        'contractor_documents')
    documents = [doc.to_dict() for doc in documents_ref.stream()]

    # Convert timestamps for display
    if 'created_at' in submission_data and hasattr(submission_data['created_at'], 'isoformat'):
        submission_data['created_at'] = submission_data['created_at'].isoformat()
    if 'updated_at' in submission_data and hasattr(submission_data['updated_at'], 'isoformat'):
        submission_data['updated_at'] = submission_data['updated_at'].isoformat()
    for doc in documents:
        if 'uploaded_at' in doc and hasattr(doc['uploaded_at'], 'isoformat'):
            doc['uploaded_at'] = doc['uploaded_at'].isoformat()

    # Get all submissions for the list on the left side
    all_submissions_ref = CONTRACTOR_PRE_APPROVALS_COLLECTION.order_by('created_at',
                                                                       direction=firestore.Query.DESCENDING)
    all_submissions = [doc.to_dict() for doc in all_submissions_ref.stream()]
    for sub in all_submissions:
        sub['id'] = sub.pop('firebase_id_field_name', None)  # Use actual Firestore ID
        # Convert Firestore Timestamp to string for display
        if 'created_at' in sub and hasattr(sub['created_at'], 'isoformat'):
            sub['created_at'] = sub['created_at'].isoformat()
        if 'updated_at' in sub and hasattr(sub['updated_at'], 'isoformat'):
            sub['updated_at'] = sub['updated_at'].isoformat()

    return render_template('hso_dashboard.html',
                           submissions=all_submissions,
                           submission_detail=submission_data,
                           documents=documents,
                           login_page=False)


@app.route('/hso/pre-approvals/<string:pre_approval_firestore_id>/update_status', methods=['POST'])
@hso_login_required
def hso_update_submission_status(pre_approval_firestore_id):
    if db is None:
        return jsonify({"success": False, "message": "Database not initialized."}), 500

    hso_id = session.get('hso_user_id')
    status = request.form.get('status')
    reason = request.form.get('reason', None)

    if status not in ['Approved', 'Declined']:
        return jsonify({"success": False, "message": "Invalid status"}), 400

    submission_doc_ref = CONTRACTOR_PRE_APPROVALS_COLLECTION.document(pre_approval_firestore_id)
    submission_doc = submission_doc_ref.get()

    if not submission_doc.exists:
        return jsonify({"success": False, "message": "Submission not found"}), 404

    submission_data = submission_doc.to_dict()

    try:
        update_data = {
            'submission_status': status,
            'approval_decline_reason': reason,
            'hso_reviewer_id': hso_id,  # Record who made the last change
            'updated_at': firestore.SERVER_TIMESTAMP
        }
        submission_doc_ref.update(update_data)

        # --- Send Email Notification ---
        contractor_email = submission_data.get('contractor_email')
        contractor_name = submission_data.get('contractor_contact_name')
        company_name = submission_data.get('company_name')
        unique_pre_approval_code = submission_data.get('unique_pre_approval_code')

        if not contractor_email:
            print(
                f"Warning: No contractor email found for submission {pre_approval_firestore_id}. Cannot send notification.")
            return jsonify(
                {"success": True, "message": "Status updated, but contractor email could not be sent (missing email)."})

        if status == 'Approved':
            subject = f"Your Documents for Factory Visit to {company_name} - Approved"
            body = f"""Dear {contractor_name},

Your documents for the upcoming visit to our factory have been reviewed and approved by our Health and Safety Officer.

Please proceed to the factory reception for your on-site registration using the app.
Your unique Pre-Approval ID is: {unique_pre_approval_code}

We look forward to your visit.

Best regards,
HC Air Conditioning Health & Safety Team
"""
            _send_email(contractor_email, subject, body)

        elif status == 'Declined':
            subject = f"Action Required: Your Factory Visit Documents for {company_name}"
            body = f"""Dear {contractor_name},

Your recent document submission for your visit to our factory requires attention.

Reason for Decline: {reason if reason else 'No specific reason provided by H&S Officer.'}

Please rectify these issues and re-email the corrected documents to {EMAIL_USER} for re-review.

Best regards,
HC Air Conditioning Health & Safety Team
"""
            _send_email(contractor_email, subject, body)

        return jsonify({"success": True, "message": "Submission status updated and contractor notified."}), 200

    except Exception as e:
        print(f"Error updating status for {pre_approval_firestore_id}: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({"success": False, "message": f"Error updating status: {e}"}), 500


@app.route('/uploads/<path:filename>')
@hso_login_required  # Ensure only logged-in HSOs can access uploaded docs directly
def uploaded_file(filename):
    """Serves uploaded files from the UPLOAD_FOLDER."""
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)


# --- Public API Endpoint for On-Site Registration App ---
@app.route('/api/public/pre-approvals/<string:pre_approval_code>')
def get_pre_approval_status(pre_approval_code):
    if db is None:
        return jsonify({"success": False, "message": "Database not initialized."}), 500

    # Validate if pre_approval_code is 5 digits
    if not (pre_approval_code.isdigit() and len(pre_approval_code) == 5):
        return jsonify({"success": False, "message": "Invalid Pre-Approval ID format. Must be 5 digits."}), 400

    submission_query = CONTRACTOR_PRE_APPROVALS_COLLECTION.where('unique_pre_approval_code', '==',
                                                                 pre_approval_code).limit(1).get()
    submission_doc = None
    for doc in submission_query:
        submission_doc = doc
        break

    if submission_doc and submission_doc.exists:
        submission_data = submission_doc.to_dict()
        # Return only necessary public info
        return jsonify({
            "success": True,
            "status": submission_data.get('submission_status'),
            "details": {
                "companyName": submission_data.get('company_name'),
                "contactName": submission_data.get('contractor_contact_name'),
                "emailAddress": submission_data.get('contractor_email'),
                "reasonForVisit": submission_data.get('project_reason_for_visit'),
                "expectedArrivalDate": submission_data.get('expected_arrival_date'),
                "approvalDeclineReason": submission_data.get('approval_decline_reason')
                # Include reason for decline case
            }
        }), 200
    else:
        return jsonify({"success": False, "message": "Invalid or expired Pre-Approval Code."}), 404


# --- Existing Routes (No changes unless specified) ---

@app.route('/')
def welcome_screen():
    return render_template('index.html')


# Factory visitor page, now including pre-approval ID logic in JS
@app.route('/factory')
def factory_visitor_page():
    return render_template('factory_visitor.html', nda_content=NDA_CONTENT)


@app.route('/office')
def office_visitor_page():
    return render_template('office_visitor.html', nda_content=NDA_CONTENT)


@app.route('/submit_factory_visit', methods=['POST'])
def submit_factory_visit():
    """Handles submission of the factory visitor form, now integrating pre-approval."""
    if db is None:
        print("Error: Database not initialized at start of submit_factory_visit.")
        return jsonify({"success": False, "message": "Database not initialized."}), 500

    try:
        form_data = request.form
        visitor_id = str(uuid.uuid4())
        selfie_photo_path = None
        selfie_photo_url = None

        # --- Handle Pre-Approval ID ---
        pre_approval_id_from_form = form_data.get('preApprovalId')
        document_acknowledgment_confirmed = form_data.get('documentAcknowledgmentConfirmed')  # from hidden field

        is_pre_approved = False
        if pre_approval_id_from_form:
            # Backend validation for 5-digit code
            if not (pre_approval_id_from_form.isdigit() and len(pre_approval_id_from_form) == 5):
                return jsonify({"success": False, "message": "Invalid Pre-Approval ID format. Must be 5 digits."}), 400

            submission_query = CONTRACTOR_PRE_APPROVALS_COLLECTION.where('unique_pre_approval_code', '==',
                                                                         pre_approval_id_from_form).limit(1).get()
            submission_doc = None
            for doc in submission_query:
                submission_doc = doc
                break

            if submission_doc and submission_doc.exists and submission_doc.to_dict().get(
                    'submission_status') == 'Approved':
                is_pre_approved = True
                # If pre-approved, retrieve contact info from pre-approval data
                pre_approval_data = submission_doc.to_dict()
                visitor_data_from_pre_approval = {
                    'firstName': pre_approval_data.get('contractor_contact_name', '').split(' ')[0],
                    'lastName': ' '.join(pre_approval_data.get('contractor_contact_name', '').split(' ')[1:]),
                    'company': pre_approval_data.get('company_name'),
                    'reasonForVisit': pre_approval_data.get('project_reason_for_visit'),
                    'emailAddress': pre_approval_data.get('contractor_email')
                }
                # Overwrite form data with pre-approved data for consistency
                # Create a mutable copy of form_data if it's an ImmutableMultiDict
                form_data_mutable = dict(form_data)
                for key, value in visitor_data_from_pre_approval.items():
                    if value:  # Only update if value from pre-approval is not empty
                        form_data_mutable[key] = value
                form_data = form_data_mutable  # Use the mutable dict for further processing

        # Handle selfie photo upload (remains mandatory for factory visitor)
        if 'selfiePhoto' in request.files:
            selfie_file = request.files['selfiePhoto']
            if selfie_file.filename != '':
                filename = secure_filename(f"{visitor_id}_selfie_{selfie_file.filename}")
                selfie_photo_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                selfie_file.save(selfie_photo_path)
                selfie_photo_url = url_for('uploaded_file', filename=filename, _external=True)
            else:
                print("Error: Selfie file has no filename.")
                return jsonify({"success": False, "message": "Selfie photo is required."}), 400
        else:
            print("Error: 'selfiePhoto' not in request.files.")
            return jsonify({"success": False, "message": "Selfie photo is required."}), 400

        # Collect final visitor data for Firestore
        # Use the (potentially updated) mutable form_data
        visitor_data = {
            'id': visitor_id,
            'type': 'Factory Visitor',
            'firstName': form_data['firstName'],
            'lastName': form_data['lastName'],
            'company': form_data['company'],
            'reasonForVisit': form_data['reasonForVisit'],
            'personVisiting': form_data['personVisiting'],
            # This remains manual input or derived if personVisiting also in pre-approval
            'emailAddress': form_data['emailAddress'],
            'selfiePhotoPath': selfie_photo_path,
            'selfiePhotoUrl': selfie_photo_url,
            'ndaAccepted': True,
            'documentAcknowledgment': is_pre_approved or (document_acknowledgment_confirmed == 'true'),
            'preApprovalIdUsed': pre_approval_id_from_form if is_pre_approved else None,  # Store the ID used
            'timestamp': firestore.SERVER_TIMESTAMP,
            'userId': f"python_backend_user_{visitor_id}",  # Consistent user ID for Canvas
        }

        # Validate required fields
        required_fields = ['firstName', 'lastName', 'company', 'reasonForVisit', 'personVisiting', 'emailAddress']
        for field in required_fields:
            if not visitor_data[field]:
                print(f"Validation Error: Missing required field: {field}")
                return jsonify({"success": False, "message": f"Missing required field: {field}"}), 400

        # Validate document acknowledgment (either pre-approved or manually acknowledged)
        if not visitor_data['documentAcknowledgment']:
            print(
                "Validation Error: Document submission acknowledgment is required or pre-approval not found/approved.")
            return jsonify({"success": False,
                            "message": "Document submission acknowledgment is required or pre-approval not found/approved."}), 400

        # Save to Firestore
        doc_ref = db.collection(f'artifacts/{APP_ID}/public/data/visitors').document(visitor_id)
        doc_ref.set(visitor_data)
        print(f"Factory Visitor data successfully saved to Firestore: {visitor_id}")

        # Send emails
        send_email_to_visitor(visitor_data['emailAddress'], visitor_data)
        send_email_to_departments('Factory Visitor', visitor_data)

        # Redirect to new contractor specific next steps page
        return jsonify({"success": True, "redirect_url": url_for('contractor_next_steps_page')})

    except Exception as e:
        print(f"Unhandled Error during factory visitor submission: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({"success": False, "message": str(e)}), 500


@app.route('/submit_office_visit', methods=['POST'])
def submit_office_visit():
    """Handles submission of the office visitor form. (No changes in this version)"""
    if db is None:
        print("Error: Database not initialized at start of submit_office_visit.")
        return jsonify({"success": False, "message": "Database not initialized."}), 500

    try:
        form_data = request.form
        visitor_id = str(uuid.uuid4())
        selfie_photo_path = None
        id_picture_path = None
        selfie_photo_url = None
        id_picture_url = None

        # Handle selfie photo upload
        if 'selfiePhoto' in request.files:
            selfie_file = request.files['selfiePhoto']
            if selfie_file.filename != '':
                filename = secure_filename(f"{visitor_id}_selfie_{selfie_file.filename}")
                selfie_photo_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                selfie_file.save(selfie_photo_path)
                selfie_photo_url = url_for('uploaded_file', filename=filename, _external=True)
            else:
                print("Error: Selfie file has no filename.")
                return jsonify({"success": False, "message": "Selfie photo is required."}), 400
        else:
            print("Error: 'selfiePhoto' not in request.files.")
            return jsonify({"success": False, "message": "Selfie photo is required."}), 400

        # Handle ID picture upload
        if 'idPicture' in request.files:
            id_file = request.files['idPicture']
            if id_file.filename != '':
                filename = secure_filename(f"{visitor_id}_id_{id_file.filename}")
                id_picture_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                id_file.save(id_picture_path)
                id_picture_url = url_for('uploaded_file', filename=filename, _external=True)
            else:
                print("Error: ID file has no filename.")
                return jsonify({"success": False, "message": "ID picture is required."}), 400
        else:
            print("Error: 'idPicture' not in request.files.")
            return jsonify({"success": False, "message": "ID picture is required."}), 400

        # Collect data for Firestore
        visitor_data = {
            'id': visitor_id,
            'type': 'Office Visitor',
            'firstName': form_data['firstName'],
            'lastName': form_data['lastName'],
            'company': form_data['company'],
            'reasonForVisit': form_data['reasonForVisit'],
            'personVisiting': form_data['personVisiting'],
            'emailAddress': form_data['emailAddress'],
            'selfiePhotoPath': selfie_photo_path,
            'selfiePhotoUrl': selfie_photo_url,
            'idPicturePath': id_picture_path,
            'idPictureUrl': id_picture_url,
            'needsWifi': form_data.get('needsWifi') == 'on',
            'ndaAccepted': True,
            'timestamp': firestore.SERVER_TIMESTAMP,
            'userId': f"python_backend_user_{visitor_id}",
        }

        # Validate required fields
        required_fields = ['firstName', 'lastName', 'company', 'reasonForVisit', 'personVisiting', 'emailAddress']
        for field in required_fields:
            if not visitor_data[field]:
                print(f"Validation Error: Missing required field: {field}")
                return jsonify({"success": False, "message": f"Missing required field: {field}"}), 400

        # Save to Firestore
        doc_ref = db.collection(f'artifacts/{APP_ID}/public/data/visitors').document(visitor_id)
        doc_ref.set(visitor_data)
        print(f"Office Visitor data successfully saved to Firestore: {visitor_id}")

        # Send emails
        send_email_to_visitor(visitor_data['emailAddress'], visitor_data)
        send_email_to_departments('Office Visitor', visitor_data)

        return jsonify({"success": True, "redirect_url": url_for('thank_you_page', visitor_type='office')})

    except Exception as e:
        print(f"Unhandled Error during office visitor submission: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({"success": False, "message": str(e)}), 500


@app.route('/contractor_next_steps')
def contractor_next_steps_page():
    """Renders the page detailing next steps for contractors."""
    return render_template('contractor_next_steps.html')


@app.route('/thank_you/<visitor_type>')
def thank_you_page(visitor_type):
    """Renders the thank you page after successful submission."""
    return render_template('thank_you.html', visitor_type=visitor_type)


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0')
