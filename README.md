# Visitor Management System

This project is a **Visitor Management System** designed to streamline the registration and management of visitors for a factory or office environment. It includes features for pre-approval of visitors, document submission, and on-site registration, with integration for email notifications and Firebase Firestore for data storage.

## Features

- **Pre-Approval System**: Visitors can enter a 5-digit pre-approval ID to auto-fill their details if pre-approved.
- **Document Submission**: Contractors can upload required documents for review by Health and Safety Officers (HSOs).
- **Selfie and ID Upload**: Visitors are required to upload a selfie and ID photo for verification.
- **Email Notifications**: Automated email notifications for visitors and relevant departments.
- **HSO Dashboard**: A secure dashboard for HSOs to review and approve contractor submissions.
- **Firebase Integration**: Firestore is used for storing visitor and contractor data.
- **NDA Agreement**: Visitors must accept a Non-Disclosure Agreement (NDA) before completing registration.

## Technologies Used

- **Backend**: Python, Flask
- **Frontend**: HTML, JavaScript
- **Database**: Firebase Firestore
- **Email**: SMTP (via `smtplib`)
- **File Uploads**: Handled using `werkzeug` for secure file handling
- **Authentication**: Session-based authentication for HSO dashboard
- **Deployment**: Flask development server (can be deployed to production environments)

## Installation

1. Clone the repository:
   ```bash
   git clone https://github.com/your-username/visitor-management-system.git
   cd visitor-management-system
## Installation

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Set up environment variables:
```bash
npm install
```

3. Create `.env` file with required variables:
```env
FLASK_SECRET_KEY: Secret key for Flask sessions.
EMAIL_USER: Email address for sending notifications.
EMAIL_PASSWORD: Password or app password for the email account.
SMTP_SERVER: SMTP server address (e.g., smtp-mail.outlook.com).
SMTP_PORT: SMTP server port (e.g., 587).
FIREBASE_SERVICE_ACCOUNT_PATH: Path to the Firebase service account JSON file.
```

4. Initialize Firebase:
Place the Firebase service account JSON file in the project directory.
Ensure Firestore is enabled in your Firebase project.

5. Run the application:
```bash
python app.py
```

6. Access the application:
Factory/Office Visitor Registration: http://localhost:5000
HSO Dashboard: http://localhost:5000/hso/login

## Usage

### Visitor Registration
- Access the main portal at `http://[your-ip]:5173`
- Choose between factory or office visitor registration
- Complete the required forms and accept policies
- Upload necessary documents (factory visitors)

### HSO Dashboard
- Access the admin dashboard at `http://[your-ip]:5173/admin`
- Review submitted documents
- Approve or reject visitor submissions
- Manage document requirements

## Project Structure

```
project/
├── src/
│   ├── components/
│   │   ├── admin/
│   │   │   └── AdminDashboard.tsx
│   │   ├── FactoryVisitorForm.tsx
│   │   └── OfficeVisitorForm.tsx
│   ├── services/
│   │   ├── documentService.ts
│   │   └── emailService.ts
│   └── App.tsx
├── server/
│   ├── routes/
│   │   ├── documents.ts
│   │   └── email.ts
│   └── index.ts
└── uploads/
```

## Security Considerations

- Document uploads are restricted to PDF, JPEG, and PNG formats
- 5MB file size limit for uploads
- Secure email integration with Office 365
- Environment-based configuration for sensitive data
- Admin authentication required for HSO dashboard

## Development

The project uses Vite for frontend development and Express for the backend server. 
To contribute:

1. Fork the repository
2. Create a feature branch
3. Submit a pull request

## License

This project is private and proprietary to HC Heat Exchangers.

## Support

For support, please contact the IT department at HC Heat Exchangers.
