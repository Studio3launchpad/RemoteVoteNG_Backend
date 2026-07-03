import logging
import requests
from django.conf import settings

logger = logging.getLogger(__name__)

def send_transactional_email(to_email, to_name, subject, html_content):
    """
    Sends an email using Brevo's Transactional Email API (v3).
    If BREVO_API_KEY is not configured or set to 'mock', it logs to console.
    """
    api_key = getattr(settings, 'BREVO_API_KEY', None)
    sender_email = getattr(settings, 'BREVO_SENDER_EMAIL', 'noreply@remotevoteng.org')
    sender_name = getattr(settings, 'BREVO_SENDER_NAME', 'RemoteVote NG')

    if not api_key or api_key == 'mock' or api_key == '':
        logger.info("=== [MOCK EMAIL SENT] ===")
        logger.info(f"To: {to_name} <{to_email}>")
        logger.info(f"Subject: {subject}")
        logger.info(f"Content: {html_content}")
        logger.info("=========================")
        return True

    url = "https://api.brevo.com/v3/smtp/email"
    headers = {
        "accept": "application/json",
        "api-key": api_key,
        "content-type": "application/json"
    }
    payload = {
        "sender": {
            "name": sender_name,
            "email": sender_email
        },
        "to": [
            {
                "email": to_email,
                "name": to_name
            }
        ],
        "subject": subject,
        "htmlContent": html_content
    }

    try:
        response = requests.post(url, json=payload, headers=headers, timeout=10)
        if response.status_code in [200, 201, 202]:
            logger.info(f"Email successfully sent to {to_email} via Brevo. Response: {response.text}")
            return True
        else:
            logger.error(f"Failed to send email to {to_email} via Brevo. Status: {response.status_code}, Response: {response.text}")
            # Still output mock details in logs for easy debugging
            logger.info(f"[Brevo Error Fallback Code] OTP for {to_email} would be in email context.")
            return False
    except Exception as e:
        logger.error(f"Exception raised while calling Brevo API: {str(e)}")
        return False


def send_otp_email(voter, otp_code, purpose):
    """
    Sends a beautiful verification OTP email to the voter.
    """
    subject = ""
    title = ""
    body_text = ""
    action_text = ""

    if purpose == 'signup':
        subject = f"{otp_code} is your RemoteVote NG verification code"
        title = "Verify Your Account"
        body_text = "Thank you for registering on RemoteVote NG. Use the secure 6-digit verification code below to verify your identity and activate your voter account."
        action_text = "This code will expire in 10 minutes. For security, never share this code with anyone."
    elif purpose == 'reset':
        subject = f"{otp_code} is your RemoteVote NG reset code"
        title = "Reset Your Password"
        body_text = "We received a request to reset your password. Use the secure 6-digit verification code below to complete the reset process."
        action_text = "If you did not make this request, please ignore this email or contact support."

    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <title>{title}</title>
        <style>
            body {{
                font-family: 'Helvetica Neue', Helvetica, Arial, sans-serif;
                background-color: #f4f6f8;
                margin: 0;
                padding: 0;
                -webkit-font-smoothing: antialiased;
            }}
            .container {{
                max-width: 600px;
                margin: 40px auto;
                background-color: #ffffff;
                border-radius: 16px;
                box-shadow: 0 4px 12px rgba(0, 0, 0, 0.05);
                overflow: hidden;
                border: 1px solid #e1e8ed;
            }}
            .header {{
                background: linear-gradient(135deg, #124024 0%, #1c6238 100%);
                padding: 30px;
                text-align: center;
                color: #ffffff;
            }}
            .header h1 {{
                margin: 0;
                font-size: 24px;
                font-weight: 700;
                letter-spacing: 0.5px;
            }}
            .content {{
                padding: 40px;
                color: #333333;
                line-height: 1.6;
            }}
            .content p {{
                margin: 0 0 20px 0;
                font-size: 16px;
            }}
            .otp-box {{
                background-color: #f0f7f3;
                border: 2px dashed #2e7d32;
                border-radius: 12px;
                padding: 20px;
                text-align: center;
                margin: 30px 0;
            }}
            .otp-code {{
                font-size: 36px;
                font-weight: 800;
                letter-spacing: 6px;
                color: #124024;
                margin: 0;
            }}
            .footer {{
                background-color: #f8fafc;
                padding: 20px 40px;
                text-align: center;
                font-size: 12px;
                color: #64748b;
                border-top: 1px solid #e2e8f0;
            }}
            .footer a {{
                color: #2e7d32;
                text-decoration: none;
            }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>RemoteVote NG</h1>
            </div>
            <div class="content">
                <p>Hello <strong>{voter.full_name}</strong>,</p>
                <p>{body_text}</p>
                <div class="otp-box">
                    <div class="otp-code">{otp_code}</div>
                </div>
                <p style="font-size: 14px; color: #64748b; font-style: italic;">{action_text}</p>
            </div>
            <div class="footer">
                <p>This is an automated security notification from the Independent National Electoral Commission (INEC).</p>
                <p>&copy; 2026 RemoteVote NG. All rights reserved.</p>
            </div>
        </div>
    </body>
    </html>
    """

    return send_transactional_email(voter.email, voter.full_name, subject, html_content)


def send_staff_invitation_email(email, role_display, staff_number, token):
    """
    Sends an onboarding invitation email to a newly pre-provisioned electoral official.
    """
    frontend_url = getattr(settings, 'FRONTEND_URL', 'http://localhost:3000')
    activation_link = f"{frontend_url}/onboard?token={token}"
    subject = "RemoteVote NG - INEC Official Onboarding Invitation"

    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <style>
            body {{ font-family: sans-serif; background-color: #f4f6f8; margin: 0; padding: 20px; }}
            .container {{ max-width: 600px; margin: 0 auto; background: #ffffff; border-radius: 12px; border: 1px solid #e2e8f0; overflow: hidden; }}
            .header {{ background: linear-gradient(135deg, #124024 0%, #1c6238 100%); padding: 24px; text-align: center; color: white; }}
            .content {{ padding: 32px; color: #334155; line-height: 1.6; }}
            .btn {{ display: inline-block; background-color: #2e7d32; color: white; padding: 12px 24px; text-decoration: none; border-radius: 8px; font-weight: bold; margin-top: 20px; }}
            .footer {{ background: #f8fafc; padding: 16px; text-align: center; font-size: 11px; color: #64748b; border-top: 1px solid #e2e8f0; }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header"><h2>RemoteVote NG Official Portal</h2></div>
            <div class="content">
                <p>Hello,</p>
                <p>You have been pre-provisioned as a <strong>{role_display}</strong> for the upcoming RemoteVote NG electoral cycle.</p>
                <p>Your official Staff Number is: <code style="background:#f1f5f9; padding:2px 6px; border-radius:4px; font-weight:bold;">{staff_number}</code></p>
                <p>To set up your security credentials (including your NIN verification challenge and official password), click the button below:</p>
                <p style="text-align: center;">
                    <a href="{activation_link}" class="btn" style="color: white;">Complete Onboarding Activation</a>
                </p>
                <p style="font-size: 12px; color: #64748b; margin-top: 24px;">Note: This invitation is single-use, secure, and will expire in 7 days.</p>
            </div>
            <div class="footer">
                <p>Independent National Electoral Commission (INEC) Security Ledger</p>
            </div>
        </div>
    </body>
    </html>
    """
    return send_transactional_email(email, "Electoral Official", subject, html_content)


def send_accreditation_approved_email(email, org_name, role):
    """
    Notifies a media house or observer group that their application has been approved.
    """
    subject = "RemoteVote NG - Accreditation APPROVED"
    role_name = "Media / Broadcaster" if role == 'media' else "Official Election Observer"

    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <style>
            body {{ font-family: sans-serif; background-color: #f4f6f8; margin: 0; padding: 20px; }}
            .container {{ max-width: 600px; margin: 0 auto; background: #ffffff; border-radius: 12px; border: 1px solid #e2e8f0; overflow: hidden; }}
            .header {{ background: #1b5e20; padding: 24px; text-align: center; color: white; }}
            .content {{ padding: 32px; color: #334155; line-height: 1.6; }}
            .footer {{ background: #f8fafc; padding: 16px; text-align: center; font-size: 11px; color: #64748b; border-top: 1px solid #e2e8f0; }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header"><h2>Accreditation Status Update</h2></div>
            <div class="content">
                <p>Hello,</p>
                <p>We are pleased to inform you that the accreditation application for <strong>{org_name}</strong> has been <strong>APPROVED</strong> for the role: <strong>{role_name}</strong>.</p>
                <p>A separate onboarding email has been dispatched containing the secure activation token to access the platform. Please check your inbox (and spam folder) for the onboarding details.</p>
            </div>
            <div class="footer">
                <p>Independent National Electoral Commission (INEC) Media & Observer Liaison Desk</p>
            </div>
        </div>
    </body>
    </html>
    """
    return send_transactional_email(email, org_name, subject, html_content)


def send_accreditation_rejected_email(email, org_name, reason):
    """
    Notifies a media house or observer group that their application has been rejected.
    """
    subject = "RemoteVote NG - Accreditation Status Update"
    reason_text = reason or "No specific notes provided by the reviewer."

    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <style>
            body {{ font-family: sans-serif; background-color: #f4f6f8; margin: 0; padding: 20px; }}
            .container {{ max-width: 600px; margin: 0 auto; background: #ffffff; border-radius: 12px; border: 1px solid #e2e8f0; overflow: hidden; }}
            .header {{ background: #b71c1c; padding: 24px; text-align: center; color: white; }}
            .content {{ padding: 32px; color: #334155; line-height: 1.6; }}
            .footer {{ background: #f8fafc; padding: 16px; text-align: center; font-size: 11px; color: #64748b; border-top: 1px solid #e2e8f0; }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header"><h2>Accreditation Status Update</h2></div>
            <div class="content">
                <p>Hello,</p>
                <p>Thank you for submitting an application for RemoteVote NG accreditation on behalf of <strong>{org_name}</strong>.</p>
                <p>After reviewing your request, the review committee has <strong>REJECTED</strong> the application at this time.</p>
                <p><strong>Review Notes:</strong></p>
                <blockquote style="background: #fdf2f2; border-left: 4px solid #b71c1c; padding: 12px; margin: 16px 0; color: #7f1d1d;">
                    {reason_text}
                </blockquote>
                <p>If you believe this decision was made in error, or if you need to update registration documents, please contact the INEC Media & Observer Liaison Desk.</p>
            </div>
            <div class="footer">
                <p>Independent National Electoral Commission (INEC) Media & Observer Liaison Desk</p>
            </div>
        </div>
    </body>
    </html>
    """
    return send_transactional_email(email, org_name, subject, html_content)

