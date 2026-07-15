document.addEventListener("DOMContentLoaded", () => {
    const form = document.getElementById("employerRegistrationForm");

    if (!form) {
        return;
    }

    const companyName = document.getElementById("company_name");
    const companyEmail = document.getElementById("company_email");
    const contactNumber = document.getElementById("contact_number");
    const password = document.getElementById("password");
    const confirmPassword = document.getElementById("confirm_password");
    const terms = document.getElementById("terms");

    const emailPattern =
        /^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$/;

    const phonePattern = /^[0-9+\-\s]{8,15}$/;

    function showError(input, errorElementId, message) {
        const errorElement = document.getElementById(errorElementId);

        input.classList.add("input-error");
        errorElement.textContent = message;
    }

    function clearError(input, errorElementId) {
        const errorElement = document.getElementById(errorElementId);

        input.classList.remove("input-error");
        errorElement.textContent = "";
    }

    form.addEventListener("submit", (event) => {
        let isValid = true;

        clearError(companyName, "companyNameError");
        clearError(companyEmail, "companyEmailError");
        clearError(contactNumber, "contactNumberError");
        clearError(password, "passwordError");
        clearError(confirmPassword, "confirmPasswordError");

        document.getElementById("termsError").textContent = "";

        if (companyName.value.trim().length < 2) {
            showError(
                companyName,
                "companyNameError",
                "Please enter your company name."
            );

            isValid = false;
        }

        if (!emailPattern.test(companyEmail.value.trim())) {
            showError(
                companyEmail,
                "companyEmailError",
                "Please enter a valid company email."
            );

            isValid = false;
        }

        if (!phonePattern.test(contactNumber.value.trim())) {
            showError(
                contactNumber,
                "contactNumberError",
                "Enter a valid contact number with 8 to 15 digits."
            );

            isValid = false;
        }

        if (password.value.length < 8) {
            showError(
                password,
                "passwordError",
                "Password must contain at least 8 characters."
            );

            isValid = false;
        }

        if (
            confirmPassword.value === "" ||
            password.value !== confirmPassword.value
        ) {
            showError(
                confirmPassword,
                "confirmPasswordError",
                "Passwords do not match."
            );

            isValid = false;
        }

        if (!terms.checked) {
            document.getElementById("termsError").textContent =
                "You must accept the terms and conditions.";

            isValid = false;
        }

        if (!isValid) {
            event.preventDefault();
        }
    });

    document.querySelectorAll(".password-toggle").forEach((button) => {
        button.addEventListener("click", () => {
            const targetId = button.dataset.target;
            const targetInput = document.getElementById(targetId);

            if (targetInput.type === "password") {
                targetInput.type = "text";
                button.textContent = "Hide";
            } else {
                targetInput.type = "password";
                button.textContent = "Show";
            }
        });
    });
});