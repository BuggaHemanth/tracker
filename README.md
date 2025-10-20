# Construction Site Transaction Tracker

A Streamlit web application for recording and tracking financial transactions at construction sites with Google Sheets integration.

## Features

- **User Authentication**: Separate login for Admin and regular Users
- **Transaction Entry**: Simple interface with text boxes for Name, Notes, and Amount
- **Transaction Types**: Paid and Received buttons (highlighted when selected)
- **Payment Modes**: Online, GPay, Phone, and Cash buttons
- **Role-Based Access**:
  - Admin: Can view all transactions from all users
  - Users: Can only view their own transactions
- **Real-time Sync**: All data stored in Google Sheets
- **Transaction History**: View past transactions with summary statistics
- **Export**: Download transactions as CSV

## Setup Instructions

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Set Up Google Cloud Service Account

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project or select an existing one
3. Enable Google Sheets API and Google Drive API:
   - Go to "APIs & Services" > "Enable APIs and Services"
   - Search for "Google Sheets API" and enable it
   - Search for "Google Drive API" and enable it
4. Create a Service Account:
   - Go to "IAM & Admin" > "Service Accounts"
   - Click "Create Service Account"
   - Name it (e.g., "streamlit-app") and create
   - Click on the service account
   - Go to "Keys" tab > "Add Key" > "Create New Key" > "JSON"
   - Download the JSON file
5. Share your Google Sheet with the service account email:
   - Open your Google Sheet: https://docs.google.com/spreadsheets/d/10H_Er872srJihxthzQJEUy7RwG6NS5q54G-Ex9VPOnI/edit
   - Click "Share" button
   - Paste the service account email (from the JSON file: `client_email`)
   - Give "Editor" permission
   - Click "Share"

### 3. Configure Secrets

Open `.streamlit/secrets.toml` and update it with your credentials:

1. Copy the contents from the downloaded JSON file
2. Replace the placeholder values in `secrets.toml` with actual values from the JSON file
3. Set your desired passwords:
   - `user_password`: Password for regular users
   - `admin_password`: Password for admin access

Example structure:
```toml
user_password = "your_user_password"
admin_password = "your_admin_password"

[gcp_service_account]
type = "service_account"
project_id = "your-project-123456"
private_key_id = "abc123..."
private_key = "-----BEGIN PRIVATE KEY-----\n...\n-----END PRIVATE KEY-----\n"
client_email = "streamlit-app@your-project.iam.gserviceaccount.com"
client_id = "123456789"
auth_uri = "https://accounts.google.com/o/oauth2/auth"
token_uri = "https://oauth2.googleapis.com/token"
auth_provider_x509_cert_url = "https://www.googleapis.com/oauth2/v1/certs"
client_x509_cert_url = "https://www.googleapis.com/robot/v1/metadata/x509/..."
universe_domain = "googleapis.com"
```

### 4. Run the Application

```bash
streamlit run app.py
```

The app will open in your browser at `http://localhost:8501`

## Usage

### Login

1. Enter your username
2. Enter password
3. Click "Login as User" or "Login as Admin"

Default credentials (change these in `.streamlit/secrets.toml`):
- User password: `user123`
- Admin password: `admin123`

### Recording a Transaction

1. Enter the **Name** of the person/vendor
2. Enter the **Amount** in rupees
3. Add any **Notes** (optional)
4. Click either **PAID** or **RECEIVED** button
5. Select payment mode: **Online**, **GPay**, **Phone**, or **Cash**
6. Click **SUBMIT TRANSACTION**

### Viewing Transactions

- **Users**: See only their own transactions
- **Admin**: See all transactions from all users
- Summary shows Total Paid, Total Received, and Balance
- Download transactions as CSV file

## Running 24/7

To keep the app running continuously:

### Option 1: Deploy to Streamlit Cloud (Free)

1. Push your code to GitHub (DO NOT commit `.streamlit/secrets.toml`)
2. Go to [share.streamlit.io](https://share.streamlit.io)
3. Sign in with GitHub
4. Deploy your app
5. Add secrets through Streamlit Cloud dashboard:
   - Go to App settings > Secrets
   - Paste the contents of your `secrets.toml` file

### Option 2: Deploy to a Server

Run with nohup (Linux):
```bash
nohup streamlit run app.py --server.port 8501 --server.address 0.0.0.0 &
```

Or use a process manager like PM2:
```bash
npm install -g pm2
pm2 start "streamlit run app.py" --name construction-txn
pm2 save
pm2 startup
```

### Option 3: Use ngrok for temporary public URL

```bash
# Install ngrok from https://ngrok.com/
streamlit run app.py &
ngrok http 8501
```

## Security Notes

- **Never commit `.streamlit/secrets.toml` to version control**
- Add `.streamlit/secrets.toml` to your `.gitignore` file
- Change default passwords before deployment
- Consider implementing stronger authentication for production use
- Use environment variables or cloud secret managers for production deployments

## Troubleshooting

### "Error connecting to Google Sheets"
- Verify that you've shared the Google Sheet with the service account email
- Check that the service account credentials in `secrets.toml` are correct
- Ensure Google Sheets API and Google Drive API are enabled in Google Cloud Console

### "Permission denied"
- Make sure the service account has "Editor" access to the Google Sheet
- Re-share the sheet if necessary

### App crashes or won't start
- Check that all dependencies are installed: `pip install -r requirements.txt`
- Verify the `secrets.toml` file is properly formatted (valid TOML syntax)
- Check for Python version compatibility (Python 3.8+ recommended)

## Support

For issues or questions, please check the Streamlit documentation at [docs.streamlit.io](https://docs.streamlit.io)
