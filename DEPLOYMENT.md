# 🚀 Deploy AI Newsletter - Free Student Options

## 🏆 Option 1: Render (Recommended)

### Why Render?
- ✅ **100% Free** (no credit card needed)
- ✅ **750 hours/month** (always-on)
- ✅ **Automatic HTTPS**
- ✅ **Easy Flask deployment**
- ✅ **Git integration**

### Steps:

1. **Create GitHub Repository**
   ```bash
   git init
   git add .
   git commit -m "Initial commit"
   git branch -M main
   git remote add origin https://github.com/yourusername/ai-newsletter.git
   git push -u origin main
   ```

2. **Sign up at render.com**
   - Go to [render.com](https://render.com)
   - Sign up with GitHub account (free)

3. **Create Web Service**
   - Click "New +" → "Web Service"
   - Connect your GitHub repository
   - Use these settings:
     - **Build Command**: `pip install -r requirements.txt`
     - **Start Command**: `gunicorn app:app`
     - **Environment**: `Python 3`

4. **Set Environment Variables**
   ```
   NEWSAPI_KEY=your_newsapi_key
   GMAIL_USER=your_gmail@gmail.com  
   GMAIL_PASS=your_app_password
   GOOGLE_SHEET_ID=your_sheet_id
   FLASK_SECRET=your_secret_key
   ```

5. **Deploy!**
   - Click "Create Web Service"
   - Your app will be live at: `https://your-app-name.onrender.com`

---

## 🎓 Option 2: Railway (Student Friendly)

### Why Railway?
- ✅ **$5/month free credit** (for students)
- ✅ **Very easy deployment**
- ✅ **Great for databases**

### Steps:
1. Sign up at [railway.app](https://railway.app)
2. Connect GitHub repo
3. Add environment variables
4. Deploy automatically

---

## 🌐 Option 3: Vercel (Frontend + Serverless)

### Why Vercel?
- ✅ **Unlimited free deployments**
- ✅ **Perfect for Flask APIs**
- ✅ **Global CDN**

### Steps:
1. Install Vercel CLI: `npm i -g vercel`
2. Create `vercel.json`:
   ```json
   {
     "builds": [{"src": "app.py", "use": "@vercel/python"}],
     "routes": [{"src": "/(.*)", "dest": "/app.py"}]
   }
   ```
3. Run: `vercel --prod`

---

## 🐙 Option 4: Heroku (Classic)

### Why Heroku?
- ✅ **Well-documented**
- ✅ **Many tutorials available**
- ✅ **550 hours/month free**

### Steps:
1. Create `Procfile`: `web: gunicorn app:app`
2. Install Heroku CLI
3. `heroku create your-app-name`
4. `git push heroku main`

---

## 🔧 Pre-Deployment Checklist

- [x] Added `gunicorn` to requirements.txt
- [x] Updated app.py for production port
- [x] Created render.yaml configuration
- [ ] Set up environment variables
- [ ] Test locally with `gunicorn app:app`
- [ ] Create GitHub repository
- [ ] Choose deployment platform

## 🎯 Recommended Flow for Students:

1. **Start with Render** (easiest, most reliable)
2. **Try Railway** if you need databases
3. **Use Vercel** for global performance
4. **Consider Heroku** for learning experience

## 🔒 Security Notes:

- Never commit `.env` files
- Use environment variables for all secrets
- Enable HTTPS (automatic on most platforms)
- Consider rate limiting in production

## 📞 Need Help?

- Render Docs: [render.com/docs](https://render.com/docs)
- Railway Docs: [docs.railway.app](https://docs.railway.app)
- Vercel Docs: [vercel.com/docs](https://vercel.com/docs)
