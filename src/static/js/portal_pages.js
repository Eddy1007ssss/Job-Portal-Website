document.addEventListener("DOMContentLoaded", () => {
    const companySearch = document.getElementById("companySearch");
    const companyCards = [
        ...document.querySelectorAll("[data-company-search]"),
    ];
    const companyNoResults = document.getElementById("companyNoResults");
    const companyResultText = document.getElementById("companyResultText");
    const clearCompanySearch = document.getElementById(
        "clearCompanySearch"
    );

    function filterCompanies() {
        if (!companySearch) {
            return;
        }

        const query = companySearch.value.trim().toLowerCase();
        let visibleCount = 0;

        companyCards.forEach((card) => {
            const searchableText = card.dataset.companySearch || "";
            const isVisible = !query || searchableText.includes(query);

            card.hidden = !isVisible;

            if (isVisible) {
                visibleCount += 1;
            }
        });

        if (companyNoResults) {
            companyNoResults.hidden = visibleCount !== 0;
        }

        if (companyResultText) {
            companyResultText.textContent =
                `Showing ${visibleCount} ` +
                (visibleCount === 1 ? "company" : "companies");
        }
    }

    companySearch?.addEventListener("input", filterCompanies);

    clearCompanySearch?.addEventListener("click", () => {
        if (!companySearch) {
            return;
        }

        companySearch.value = "";
        filterCompanies();
        companySearch.focus();
    });

    document
        .querySelectorAll("[data-password-toggle]")
        .forEach((button) => {
            button.addEventListener("click", () => {
                const input = document.getElementById(
                    button.dataset.passwordToggle
                );

                if (!input) {
                    return;
                }

                const shouldShow = input.type === "password";
                input.type = shouldShow ? "text" : "password";

                const icon = button.querySelector("i");
                icon?.classList.toggle("fa-eye", !shouldShow);
                icon?.classList.toggle("fa-eye-slash", shouldShow);

                const label = button.querySelector(".sr-only");

                if (label) {
                    label.textContent = shouldShow
                        ? "Hide password"
                        : "Show password";
                }
            });
        });

    const newPassword = document.getElementById("newPassword");
    const confirmPassword = document.getElementById("confirmPassword");

    function validatePasswordMatch() {
        if (!newPassword || !confirmPassword) {
            return;
        }

        const message =
            confirmPassword.value &&
            newPassword.value !== confirmPassword.value
                ? "New passwords do not match."
                : "";
        confirmPassword.setCustomValidity(message);
    }

    newPassword?.addEventListener("input", validatePasswordMatch);
    confirmPassword?.addEventListener("input", validatePasswordMatch);

    document.querySelectorAll(".portal-flash").forEach((message) => {
        window.setTimeout(() => {
            message.classList.add("hide");

            window.setTimeout(() => message.remove(), 250);
        }, 3500);
    });
});
