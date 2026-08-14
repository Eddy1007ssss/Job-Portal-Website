import smtplib
from email.message import EmailMessage

from flask import (
    Blueprint,
    current_app,
    flash,
    redirect,
    render_template,
    request,
    session,
    url_for,
)

from src.database import get_db_connection
from src.password_reset_logic import (
    ACCOUNT_TABLES,
    create_password_reset_token,
    get_password_reset_token_status,
    reset_account_password,
    validate_email_address,
)

password_reset_bp = Blueprint("password_reset", __name__)


@password_reset_bp.route(
    "/forgot-password",
    methods=["GET", "POST"],
)
def request_password_reset():
    account_type = request.values.get("account_type", "seeker").strip().lower()

    if account_type not in ACCOUNT_TABLES:
        account_type = "seeker"

    if request.method == "GET":
        return render_template(
            "forgot_password.html",
            account_type=account_type,
            submitted=False,
        )

    email = request.form.get("email", "").strip().lower()
    email_error = validate_email_address(email)

    if email_error:
        flash(email_error, "error")
        return render_template(
            "forgot_password.html",
            account_type=account_type,
            email=email,
            submitted=False,
        )

    connection = get_db_connection()
    token = create_password_reset_token(
        connection,
        email,
        account_type,
    )
    connection.close()
    demo_reset_url = None

    if token:
        reset_url = url_for(
            "password_reset.reset_password_page",
            token=token,
            _external=True,
        )
        delivered = send_password_reset_email(email, reset_url)

        if not delivered and (current_app.debug or current_app.testing):
            demo_reset_url = reset_url

    return render_template(
        "forgot_password.html",
        account_type=account_type,
        email=email,
        submitted=True,
        demo_reset_url=demo_reset_url,
    )


@password_reset_bp.route(
    "/reset-password/<token>",
    methods=["GET", "POST"],
)
def reset_password_page(token: str):
    connection = get_db_connection()

    if request.method == "GET":
        token_status = get_password_reset_token_status(connection, token)
        connection.close()
        return render_template(
            "reset_password.html",
            token=token,
            token_valid=token_status.outcome == "valid",
            token_message=token_status.message,
            account_type=token_status.account_type or "seeker",
        )

    result = reset_account_password(
        connection,
        token,
        request.form.get("new_password", ""),
        request.form.get("confirm_password", ""),
    )
    connection.close()

    if result.succeeded:
        session.clear()
        flash(result.message, "success")
        login_endpoint = ACCOUNT_TABLES[result.account_type or "seeker"][
            "login_endpoint"
        ]
        return redirect(url_for(login_endpoint))

    return render_template(
        "reset_password.html",
        token=token,
        token_valid=result.outcome not in {"invalid", "expired"},
        token_message=result.message,
        account_type=result.account_type or "seeker",
    )


def send_password_reset_email(email: str, reset_url: str) -> bool:
    """Send through configured SMTP; local debug mode shows a preview."""

    mail_server = current_app.config.get("MAIL_SERVER", "")

    if not mail_server:
        return False

    message = EmailMessage()
    message["Subject"] = "Reset your JobPortal password"
    message["From"] = current_app.config["MAIL_DEFAULT_SENDER"]
    message["To"] = email
    message.set_content(
        "A password reset was requested for your JobPortal account.\n\n"
        f"Reset your password using this link:\n{reset_url}\n\n"
        "The link expires in 30 minutes and can only be used once. "
        "If you did not request this change, you can ignore this email."
    )

    use_ssl = bool(current_app.config.get("MAIL_USE_SSL"))
    smtp_class = smtplib.SMTP_SSL if use_ssl else smtplib.SMTP

    try:
        with smtp_class(
            mail_server,
            int(current_app.config.get("MAIL_PORT", 587)),
            timeout=10,
        ) as smtp:
            if current_app.config.get("MAIL_USE_TLS") and not use_ssl:
                smtp.starttls()

            username = current_app.config.get("MAIL_USERNAME", "")

            if username:
                smtp.login(
                    username,
                    current_app.config.get("MAIL_PASSWORD", ""),
                )

            smtp.send_message(message)
    except OSError, smtplib.SMTPException:
        current_app.logger.exception("Unable to send password reset email.")
        return False

    return True
