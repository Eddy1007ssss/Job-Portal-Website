document.addEventListener("DOMContentLoaded", function () {
    const passwordField = document.getElementById("newPassword");
    const confirmField = document.getElementById("confirmPassword");
    const matchMessage = document.getElementById("passwordMatchMessage");

    document
        .querySelectorAll("[data-password-toggle]")
        .forEach(function (button) {
            button.addEventListener("click", function () {
                const field = document.getElementById(
                    button.dataset.passwordToggle
                );

                if (!field) {
                    return;
                }

                const showPassword = field.type === "password";
                field.type = showPassword ? "text" : "password";
                button.setAttribute(
                    "aria-label",
                    showPassword ? "Hide password" : "Show password"
                );

                const icon = button.querySelector("i");

                if (icon) {
                    icon.classList.toggle("fa-eye", !showPassword);
                    icon.classList.toggle("fa-eye-slash", showPassword);
                }
            });
        });

    if (!passwordField || !confirmField) {
        return;
    }

    const rules = {
        length: function (password) {
            return password.length >= 8;
        },
        uppercase: function (password) {
            return /[A-Z]/.test(password);
        },
        lowercase: function (password) {
            return /[a-z]/.test(password);
        },
        number: function (password) {
            return /[0-9]/.test(password);
        },
    };

    function updatePasswordRules() {
        const password = passwordField.value;

        Object.entries(rules).forEach(function ([ruleName, validator]) {
            const ruleElement = document.querySelector(
                `[data-rule="${ruleName}"]`
            );

            if (ruleElement) {
                ruleElement.classList.toggle("valid", validator(password));
            }
        });
    }

    function updatePasswordMatch() {
        if (!matchMessage) {
            return;
        }

        if (!confirmField.value) {
            matchMessage.textContent = "";
            matchMessage.classList.remove("valid");
            return;
        }

        const passwordsMatch = passwordField.value === confirmField.value;
        matchMessage.textContent = passwordsMatch
            ? "Passwords match."
            : "Passwords do not match.";
        matchMessage.classList.toggle("valid", passwordsMatch);
    }

    passwordField.addEventListener("input", function () {
        updatePasswordRules();
        updatePasswordMatch();
    });
    confirmField.addEventListener("input", updatePasswordMatch);
});
