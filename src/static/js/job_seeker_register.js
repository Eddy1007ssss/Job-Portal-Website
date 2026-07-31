"use strict";

const EMAIL_PATTERN = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
const PHONE_PATTERN = /^\+?[0-9]{8,15}$/;

function normalizePhone(value) {
    const prefix = value.trim().startsWith("+") ? "+" : "";
    return prefix + value.replace(/\D/g, "");
}

function setFieldError(field, message) {
    const error = document.getElementById(`${field.id}-error`);
    field.setAttribute("aria-invalid", message ? "true" : "false");
    if (error) {
        error.textContent = message;
    }
}

function validateRegistrationForm(form) {
    const fullName = form.elements.full_name;
    const email = form.elements.email;
    const phone = form.elements.phone_number;
    const password = form.elements.password;
    const confirmPassword = form.elements.confirm_password;
    let isValid = true;

    if (fullName.value.trim().length < 2) {
        setFieldError(fullName, "Enter your full name using at least 2 characters.");
        isValid = false;
    } else {
        setFieldError(fullName, "");
    }

    if (!EMAIL_PATTERN.test(email.value.trim())) {
        setFieldError(email, "Enter a valid email address.");
        isValid = false;
    } else {
        setFieldError(email, "");
    }

    if (!PHONE_PATTERN.test(normalizePhone(phone.value))) {
        setFieldError(phone, "Enter a phone number containing 8 to 15 digits.");
        isValid = false;
    } else {
        setFieldError(phone, "");
    }

    let passwordError = "";
    if (password.value.length < 8) {
        passwordError = "Password must contain at least 8 characters.";
    } else if (!/[A-Z]/.test(password.value)) {
        passwordError = "Password must include an uppercase letter.";
    } else if (!/[a-z]/.test(password.value)) {
        passwordError = "Password must include a lowercase letter.";
    } else if (!/[0-9]/.test(password.value)) {
        passwordError = "Password must include a number.";
    }
    setFieldError(password, passwordError);
    isValid = isValid && !passwordError;

    const confirmError = confirmPassword.value === password.value
        ? ""
        : "The passwords do not match.";
    setFieldError(confirmPassword, confirmError);
    isValid = isValid && !confirmError;

    return isValid;
}

document.addEventListener("DOMContentLoaded", () => {
    const form = document.getElementById("registration-form");
    if (!form) {
        return;
    }

    document.querySelectorAll("[data-toggle-password]").forEach((button) => {
        button.addEventListener("click", () => {
            const field = document.getElementById(button.dataset.togglePassword);
            const reveal = field.type === "password";
            field.type = reveal ? "text" : "password";
            button.textContent = reveal ? "Hide" : "Show";
            button.setAttribute("aria-label", `${reveal ? "Hide" : "Show"} password`);
        });
    });

    form.addEventListener("submit", (event) => {
        if (!validateRegistrationForm(form)) {
            event.preventDefault();
            const firstInvalidField = form.querySelector('[aria-invalid="true"]');
            firstInvalidField?.focus();
        }
    });

    form.querySelectorAll("input:not([type='hidden'])").forEach((field) => {
        field.addEventListener("input", () => {
            if (field.getAttribute("aria-invalid") === "true") {
                setFieldError(field, "");
            }
        });
    });
});
