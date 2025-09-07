# AI Newsletter

A modern, AI-powered newsletter subscription service with OTP verification, built with Flask and deployed on Render.

## Features

- 🔐 **Secure OTP Verification** - Email-based verification system
- 📱 **Responsive Design** - Modern UI with Tailwind CSS
- 📧 **Newsletter Management** - Subscribe, manage preferences, unsubscribe
- 📰 **Trending News** - Real-time news from NewsAPI
- 🛡️ **Security Features** - Rate limiting, input validation, secure OTP generation
- 👤 **User Management** - Session-based authentication
- 📊 **Admin Dashboard** - Basic subscriber statistics

## Tech Stack

- **Backend**: Flask (Python)
- **Frontend**: HTML, Tailwind CSS, JavaScript
- **Database**: Google Sheets API
- **Email**: Gmail SMTP
- **News**: NewsAPI
- **Deployment**: Render

## Quick Start

1. **Clone the repository**
   ```bash
   git clone https://github.com/YuvrajGupta1808/ai-newsletter.git
   cd ai-newsletter
   ```

2. **Set up environment variables**
   ```bash
   cp env.example .env
   # Edit .env with your API keys
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Run locally**
   ```bash
   python app.py
   ```

## Environment Variables

Create a `.env` file with the following variables:

```env
NEWSAPI_KEY=your_newsapi_key
GMAIL_USER=your_email@gmail.com
GMAIL_PASS=your_gmail_app_password
GOOGLE_SHEET_ID=your_google_sheet_id
FLASK_SECRET=your_secret_key
GOOGLE_CREDENTIALS_JSON=your_google_credentials_json
```

## Deployment

This app is configured for deployment on Render:

1. Connect your GitHub repository to Render
2. Set environment variables in Render dashboard
3. Deploy automatically

## API Endpoints

- `GET /` - Homepage with trending news
- `GET /subscribe` - Subscription form
- `POST /subscribe` - Process subscription
- `GET /verify` - OTP verification page
- `POST /verify` - Verify OTP
- `GET /manage` - Manage subscription
- `GET /trending` - Trending news page
- `GET /about` - About page
- `GET /admin` - Admin dashboard

## Security Features

- Rate limiting on sensitive endpoints
- Input validation and sanitization
- Secure OTP generation
- Environment variable protection
- Session management

## License

MIT License - feel free to use this project for learning and development.

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Submit a pull request

---

Built with ❤️ by [YuvrajGupta1808](https://github.com/YuvrajGupta1808)
