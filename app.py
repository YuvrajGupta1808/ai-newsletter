from flask import Flask, render_template, request, redirect, flash, session
import re
import random
from datetime import datetime, timedelta
from dotenv import load_dotenv
import logging

# Load environment variables
load_dotenv()

from config import TOPICS, FLASK_SECRET
from utils import (
    validate_email_address, 
    validate_topics, 
    sanitize_input,
    simple_rate_limit,
    generate_secure_otp,
    validate_otp_format,
    log_security_event
)
from sheets import (
    upsert_subscriber,
    is_verified,
    set_pending_subscription,
    verify_otp,
    update_preferences,
    get_subscriber,
    set_otp,
    unsubscribe_user,
    deactivate_subscription,
)
from news import fetch_news, build_html
from mailer import send_email
from cache import cached_fetch_news

app = Flask(__name__)
app.secret_key = FLASK_SECRET

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('newsletter.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

def create_verification_email(otp_code, purpose="subscription"):
    """Create a professional verification email template"""
    purpose_text = {
        "subscription": {
            "title": "Verify your newsletter subscription",
            "heading": "Welcome to AI Newsletter! 🎉",
            "message": "Thank you for subscribing! Please verify your email address to complete your subscription and start receiving personalized news updates.",
            "button_text": "Verify Subscription"
        },
        "manage": {
            "title": "Verify access to manage subscription",
            "heading": "Verify Your Identity 🔐",
            "message": "You requested access to manage your subscription preferences. Please verify your email address to continue.",
            "button_text": "Access Management"
        }
    }
    
    content = purpose_text.get(purpose, purpose_text["subscription"])
    
    return f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>{content['title']}</title>
        <style>
            * {{ margin: 0; padding: 0; box-sizing: border-box; }}
            body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, sans-serif; background-color: #f8fafc; }}
            .container {{ max-width: 600px; margin: 0 auto; background-color: #ffffff; }}
            .header {{ background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); padding: 40px 30px; text-align: center; }}
            .header h1 {{ color: #ffffff; font-size: 28px; font-weight: 700; margin-bottom: 8px; }}
            .header p {{ color: #e2e8f0; font-size: 16px; }}
            .content {{ padding: 40px 30px; }}
            .message {{ color: #334155; font-size: 16px; line-height: 1.6; margin-bottom: 30px; }}
            .code-container {{ background: linear-gradient(135deg, #f1f5f9 0%, #e2e8f0 100%); border-radius: 12px; padding: 30px; text-align: center; margin: 30px 0; border: 2px dashed #cbd5e1; }}
            .code-label {{ color: #64748b; font-size: 14px; font-weight: 600; margin-bottom: 12px; text-transform: uppercase; letter-spacing: 0.5px; }}
            .verification-code {{ font-size: 36px; font-weight: 800; color: #1e293b; font-family: 'Courier New', monospace; letter-spacing: 4px; margin: 12px 0; text-shadow: 0 2px 4px rgba(0,0,0,0.1); }}
            .expiry {{ color: #64748b; font-size: 13px; margin-top: 12px; }}
            .button {{ display: inline-block; background: linear-gradient(135deg, #3b82f6 0%, #8b5cf6 100%); color: #ffffff; text-decoration: none; padding: 16px 32px; border-radius: 8px; font-weight: 600; font-size: 16px; margin: 20px 0; box-shadow: 0 4px 12px rgba(59, 130, 246, 0.3); }}
            .footer {{ background-color: #f8fafc; padding: 30px; text-align: center; border-top: 1px solid #e2e8f0; }}
            .footer-text {{ color: #64748b; font-size: 14px; line-height: 1.5; }}
            .footer-links {{ margin-top: 16px; }}
            .footer-links a {{ color: #3b82f6; text-decoration: none; margin: 0 12px; font-size: 14px; }}
            .security-notice {{ background-color: #fef3c7; border: 1px solid #fbbf24; border-radius: 8px; padding: 16px; margin: 20px 0; }}
            .security-notice-text {{ color: #92400e; font-size: 14px; }}
            @media (max-width: 600px) {{
                .container {{ margin: 0; }}
                .header, .content, .footer {{ padding: 20px; }}
                .verification-code {{ font-size: 28px; letter-spacing: 2px; }}
            }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>AI Newsletter</h1>
                <p>{content['heading']}</p>
            </div>
            
            <div class="content">
                <p class="message">{content['message']}</p>
                
                <div class="code-container">
                    <div class="code-label">Your Verification Code</div>
                    <div class="verification-code">{otp_code}</div>
                    <div class="expiry">⏰ This code expires in 10 minutes</div>
                </div>
                
                <div class="security-notice">
                    <div class="security-notice-text">
                        🔒 <strong>Security Notice:</strong> Never share this code with anyone. We will never ask for your verification code via phone or email.
                    </div>
                </div>
            </div>
            
            <div class="footer">
                <p class="footer-text">
                    This email was sent because you requested verification for AI Newsletter.<br>
                    If you didn't request this, please ignore this email.
                </p>
                <div class="footer-links">
                    <a href="#">Privacy Policy</a>
                    <a href="#">Contact Support</a>
                    <a href="#">Unsubscribe</a>
                </div>
                <p class="footer-text" style="margin-top: 16px; font-size: 12px; color: #94a3b8;">
                    © 2024 AI Newsletter. All rights reserved.
                </p>
            </div>
        </div>
    </body>
    </html>
    """

@app.route("/", methods=["GET"])
def index():
    # GET → include trending news for the homepage (no subscribe form here)
    trending = {}
    try:
        for t in TOPICS:
            trending[t] = cached_fetch_news(t, 3, cache_ttl=600)  # Cache for 10 minutes
    except Exception as e:
        logger.error(f"Failed to fetch trending news: {e}")
        trending = {}
    
    # Check if current user is subscribed (for conditional UI)
    user_email = session.get('email')
    is_subscribed = False
    if user_email:
        try:
            is_subscribed = is_verified(user_email)
        except Exception as e:
            logger.error(f"Error checking subscription status for {user_email}: {e}")
    
    return render_template("index.html", 
                         trending=trending,
                         is_subscribed=is_subscribed,
                         user_email=user_email)

@app.route("/subscribe", methods=["GET", "POST"])
def subscribe():
    if request.method == "POST":
        # Sanitize inputs
        email = sanitize_input(request.form.get("email", ""))
        topics = [sanitize_input(topic) for topic in request.form.getlist("topics")]

        # Validate email
        validated_email = validate_email_address(email)
        if not validated_email:
            log_security_event("INVALID_EMAIL_ATTEMPT", f"Email: {email}")
            flash("❌ Please enter a valid email address.", "error")
            return redirect("/subscribe")
        
        # Validate topics
        if not validate_topics(topics, TOPICS):
            log_security_event("INVALID_TOPICS_ATTEMPT", f"Topics: {topics}")
            flash("⚠️ Please select valid categories only.", "error")
            return redirect("/subscribe")
        
        email = validated_email

        max_items = 3
        try:
            if is_verified(email):
                flash("You are already subscribed and verified. Manage your preferences below.", "success")
                return redirect(f"/manage?email={email}")
        except Exception as e:
            flash(f"❌ Could not check subscription: {e}", "error")
            return redirect("/subscribe")

        try:
            otp_code = generate_secure_otp()  # Secure 6-digit OTP
            expires_at = (datetime.utcnow() + timedelta(minutes=10)).isoformat(timespec="seconds") + "Z"
            action, row_idx = set_pending_subscription(email, topics, max_items=max_items, otp_code=otp_code, otp_expires_iso=expires_at)
            logger.info(f"Set pending subscriber: {action}, row: {row_idx}, email: {email}")
        except Exception as e:
            logger.error(f"Could not start verification for {email}: {e}")
            flash(f"❌ Could not start verification: {e}", "error")
            return redirect("/subscribe")

        try:
            html = create_verification_email(otp_code, "subscription")
            ok = send_email(email, "Verify your newsletter subscription", html)
            if not ok:
                flash("⚠️ Could not send verification code. Try again later.", "error")
                return redirect("/subscribe")
        except Exception as e:
            flash(f"⚠️ Failed to send verification code: {e}", "error")
            return redirect("/subscribe")

        return redirect(f"/verify?email={email}")

    return render_template("subscribe.html", topics=TOPICS)

@app.route("/thank-you")
def thank_you():
    return render_template("thankyou.html")

@app.route("/health")
def health():
    return "ok"

@app.route("/verify", methods=["GET", "POST"])
@simple_rate_limit(max_requests=20, window_seconds=300)  # 20 attempts per 5 minutes (dev testing)
def verify():
    # Auto-send OTP if coming from GET with email (first visit or resend)
    if request.method == "GET":
        email = request.args.get("email", "").strip()
        if email:
            try:
                otp_code = generate_secure_otp()
                expires_at = (datetime.utcnow() + timedelta(minutes=10)).isoformat(timespec="seconds") + "Z"
                set_otp(email, otp_code, expires_at)
                html = create_verification_email(otp_code, "subscription")
                send_email(email, "Verify your newsletter subscription", html)
                flash("We sent you a fresh verification code.", "success")
            except Exception as e:
                flash(f"⚠️ Could not send verification code: {e}", "error")
        return render_template("verify.html", email=email)

    if request.method == "POST":
        # Sanitize inputs
        email = sanitize_input(request.form.get("email", ""))
        otp = sanitize_input(request.form.get("otp", ""))
        
        # Validate inputs
        validated_email = validate_email_address(email)
        if not validated_email or not validate_otp_format(otp):
            log_security_event("INVALID_VERIFICATION_ATTEMPT", f"Email: {email}, OTP format: {bool(validate_otp_format(otp))}")
            flash("❌ Invalid email or OTP format.", "error")
            return redirect("/verify")
        
        email = validated_email
        try:
            ok = verify_otp(email, otp)
            if not ok:
                flash("❌ Invalid or expired OTP.", "error")
                return redirect(f"/verify?email={email}")
            # On success, send first digest based on current preferences
            rec, _, _ = get_subscriber(email)
            selected = []
            for t in TOPICS:
                if str(rec.get(t, "")).upper() == "TRUE":
                    selected.append(t)
            max_items = int(rec.get("Max_items", "3") or 3)
            if selected:
                all_news = {t: fetch_news(t, max_items) for t in selected}
                html = build_html(all_news)
                send_email(email, f"Your Daily Digest - {', '.join(selected)}", html)
            session["email"] = email
            flash("✅ Subscription verified!", "success")
            return redirect("/thank-you")
        except Exception as e:
            flash(f"❌ Verification failed: {e}", "error")
            return redirect("/verify")

    # Fallback
    email = request.args.get("email", "").strip()
    return render_template("verify.html", email=email)

@app.route("/resend-otp", methods=["POST"])
def resend_otp():
    email = request.form.get("email", "").strip()
    if not email:
        flash("❌ Email is required to resend code.", "error")
        return redirect("/")
    try:
        otp_code = generate_secure_otp()
        expires_at = (datetime.utcnow() + timedelta(minutes=10)).isoformat(timespec="seconds") + "Z"
        set_otp(email, otp_code, expires_at)
        html = create_verification_email(otp_code, "subscription")
        send_email(email, "Your verification code", html)
        flash("A new verification code has been sent.", "success")
    except Exception as e:
        flash(f"⚠️ Could not resend code: {e}", "error")
    return redirect(f"/verify?email={email}")

@app.route("/manage", methods=["GET", "POST"])
def manage():
    if request.method == "POST":
        # Check if this is an email verification request or preference update
        action = request.form.get("action", "")
        
        if action == "verify_email":
            # User wants to verify their email to manage preferences
            email = sanitize_input(request.form.get("email", ""))
            validated_email = validate_email_address(email)
            
            if not validated_email:
                flash("❌ Please enter a valid email address.", "error")
                return redirect("/manage")
            
            # Check if user exists and is verified
            try:
                if not is_verified(validated_email):
                    flash("⚠️ Email not found or not verified. Please subscribe first.", "error")
                    return redirect("/subscribe")
                
                # Generate OTP for manage access
                otp_code = generate_secure_otp()
                expires_at = (datetime.utcnow() + timedelta(minutes=10)).isoformat(timespec="seconds") + "Z"
                set_otp(validated_email, otp_code, expires_at)
                
                # Send OTP email
                html = create_verification_email(otp_code, "manage")
                send_email(validated_email, "Verify access to manage subscription", html)
                flash("✅ Verification code sent to your email.", "success")
                return redirect(f"/manage-verify?email={validated_email}")
                
            except Exception as e:
                logger.error(f"Error in manage email verification: {e}")
                flash("❌ An error occurred. Please try again.", "error")
                return redirect("/manage")
        
        else:
            # This is a preference update - user should be logged in
            email = session.get('email')
            if not email:
                flash("❌ Please verify your email first.", "error")
                return redirect("/manage")
            
            topics = [sanitize_input(topic) for topic in request.form.getlist("topics")]
            
            if not validate_topics(topics, TOPICS):
                flash("⚠️ Please select valid categories only.", "error")
                return redirect(f"/manage?email={email}")
            
            try:
                ok = update_preferences(email, topics)
                if ok:
                    flash("✅ Preferences updated successfully.", "success")
                else:
                    flash("❌ Could not update preferences.", "error")
            except Exception as e:
                logger.error(f"Failed to update preferences for {email}: {e}")
                flash(f"❌ Failed to update preferences: {e}", "error")
            
            return redirect(f"/manage?email={email}")

    # GET request - show appropriate form based on user state
    email = request.args.get("email", "").strip() or session.get('email', '')
    current = {t: False for t in TOPICS}
    user_verified = False
    
    if email:
        try:
            if is_verified(email):
                user_verified = True
                rec, _, _ = get_subscriber(email)
                if rec:
                    for t in TOPICS:
                        current[t] = str(rec.get(t, "")).upper() == "TRUE"
        except Exception as e:
            logger.error(f"Error checking user verification status: {e}")
    
    return render_template("manage.html", 
                         topics=TOPICS, 
                         current=current, 
                         email=email,
                         user_verified=user_verified,
                         is_logged_in=bool(session.get('email')))

@app.route("/manage-verify", methods=["GET", "POST"])
@simple_rate_limit(max_requests=20, window_seconds=300)  # 20 attempts per 5 minutes (dev testing)
def manage_verify():
    email = request.args.get("email", "").strip()
    
    if not email:
        flash("❌ Email parameter missing.", "error")
        return redirect("/manage")
    
    if request.method == "POST":
        otp = sanitize_input(request.form.get("otp", ""))
        
        if not validate_otp_format(otp):
            flash("❌ Invalid OTP format.", "error")
            return redirect(f"/manage-verify?email={email}")
        
        try:
            ok = verify_otp(email, otp)
            if ok:
                # Set session for manage access
                session['email'] = email
                session['manage_verified'] = True
                flash("✅ Access verified! You can now manage your preferences.", "success")
                return redirect(f"/manage?email={email}")
            else:
                flash("❌ Invalid or expired OTP.", "error")
                return redirect(f"/manage-verify?email={email}")
        except Exception as e:
            logger.error(f"Manage verification error for {email}: {e}")
            flash("❌ Verification failed. Please try again.", "error")
            return redirect(f"/manage-verify?email={email}")
    
    return render_template("manage_verify.html", email=email)

@app.route("/trending")
def trending():
    data = {}
    try:
        for t in TOPICS:
            data[t] = cached_fetch_news(t, 6, cache_ttl=300)  # Cache for 5 minutes
    except Exception as e:
        logger.error(f"Failed to fetch trending news: {e}")
        data = {}
    return render_template("trending.html", trending=data)

@app.route("/about")
def about():
    return render_template("about.html")

@app.route("/logout")
def logout():
    session.clear()
    flash("You have been logged out.", "success")
    return redirect("/")

@app.route("/unsubscribe", methods=["GET", "POST"])
def unsubscribe():
    if request.method == "POST":
        email = sanitize_input(request.form.get("email", ""))
        action = request.form.get("action", "")
        
        validated_email = validate_email_address(email)
        if not validated_email:
            flash("❌ Please enter a valid email address.", "error")
            return redirect("/unsubscribe")
        
        email = validated_email
        
        try:
            if action == "deactivate":
                success = deactivate_subscription(email)
                if success:
                    flash("✅ Your subscription has been deactivated. You can reactivate anytime.", "success")
                else:
                    flash("❌ Email not found in our system.", "error")
            elif action == "delete":
                success = unsubscribe_user(email)
                if success:
                    flash("✅ You have been completely unsubscribed. All your data has been removed.", "success")
                else:
                    flash("❌ Email not found in our system.", "error")
            else:
                flash("❌ Invalid action.", "error")
                
        except Exception as e:
            logger.error(f"Unsubscribe error for {email}: {e}")
            flash("❌ An error occurred. Please try again later.", "error")
        
        return redirect("/unsubscribe")
    
    return render_template("unsubscribe.html")

@app.route("/admin")
def admin_dashboard():
    """Basic admin dashboard - in production, add proper authentication"""
    try:
        from sheets import open_sheet_with_retry, ensure_headers
        
        sheet = open_sheet_with_retry()
        headers = ensure_headers(sheet)
        records = sheet.get_all_records(expected_headers=headers)
        
        # Calculate statistics
        total_subscribers = len(records)
        verified_subscribers = sum(1 for r in records if str(r.get("Verified", "")).upper() == "TRUE")
        active_subscribers = sum(1 for r in records if str(r.get("Active", "TRUE")).upper() == "TRUE")
        
        # Topic preferences
        topic_stats = {}
        for topic in TOPICS:
            topic_stats[topic] = sum(1 for r in records if str(r.get(topic, "")).upper() == "TRUE")
        
        # Recent signups (last 10)
        recent_signups = sorted(
            [r for r in records if r.get("Timestamp")],
            key=lambda x: x.get("Timestamp", ""),
            reverse=True
        )[:10]
        
        stats = {
            'total_subscribers': total_subscribers,
            'verified_subscribers': verified_subscribers,
            'active_subscribers': active_subscribers,
            'unverified_subscribers': total_subscribers - verified_subscribers,
            'topic_stats': topic_stats,
            'recent_signups': recent_signups
        }
        
        return render_template("admin.html", stats=stats, topics=TOPICS)
        
    except Exception as e:
        logger.error(f"Admin dashboard error: {e}")
        flash(f"❌ Could not load admin dashboard: {e}", "error")
        return redirect("/")

if __name__ == "__main__":
    import os
    port = int(os.environ.get("PORT", 5001))
    app.run(debug=True, host="0.0.0.0", port=port)