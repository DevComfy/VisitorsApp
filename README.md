# HC Visitor Management System

A modern web-based visitor management system designed for HC Heat Exchangers to streamline the registration and management of visitors for factory and office environments. The system includes features for document submission, email notifications, and a dedicated HSO (Health and Safety Officer) dashboard.

## Features

- **Dual Registration System**: Separate flows for factory and office visitors
- **Document Submission**: Contractors can submit required safety documents for HSO review
- **Email Notifications**: Automated notifications for visitors and HSO
- **HSO Dashboard**: Secure interface for reviewing and approving contractor submissions
- **NDA & Policy Management**: Digital acceptance of NDAs and factory policies
- **Real-time Status Updates**: Track document approval status

## Tech Stack

- **Frontend**: React, TypeScript, Tailwind CSS, Lucide Icons
- **Backend**: Node.js, Express
- **Email**: Nodemailer with Office 365 integration
- **File Handling**: Multer for document uploads
- **Authentication**: Environment-based admin authentication

## Installation

1. Clone the repository:
```bash
git clone [repository-url]
cd project
```

2. Install dependencies:
```bash
npm install
```

3. Create `.env` file with required variables:
```env
EMAIL_USER=no-reply@hcaircon.com
EMAIL_PASS=your-email-password
PORT=3000
VITE_ADMIN_EMAIL=hso@example.com
VITE_ADMIN_PASSWORD=your-admin-password
```

4. Start the development server:
```bash
npm run dev
```

5. Start the backend server:
```bash
npm run server
```

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
