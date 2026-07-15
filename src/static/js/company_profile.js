document.addEventListener("DOMContentLoaded", () => {
    const form = document.getElementById("companyProfileForm");
    const description = document.getElementById("company_description");
    const counter = document.getElementById("descriptionCounter");

    if (!form || !description || !counter) {
        return;
    }

    function updateCounter() {
        counter.textContent = `${description.value.length} / 1500`;
    }

    updateCounter();

    description.addEventListener("input", updateCounter);

    form.addEventListener("submit", (event) => {
        let isValid = true;

        const companyName = document.getElementById("company_name");
        const industry = document.getElementById("industry");
        const address = document.getElementById("address");
        const contactEmail = document.getElementById("contact_email");
        const contactNumber = document.getElementById("contact_number");

        const emailPattern =
            /^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$/;

        const phonePattern = /^[0-9+\-\s]{8,15}$/;

        document.querySelectorAll(".field-error").forEach((element) => {
            element.textContent = "";
        });

        document.querySelectorAll(
            ".form-group input, .form-group select, .form-group textarea"
        ).forEach((element) => {
            element.classList.remove("input-error");
        });

        function addError(input, errorId, message) {
            input.classList.add("input-error");
            document.getElementById(errorId).textContent = message;
            isValid = false;
        }

        if (companyName.value.trim().length < 2) {
            addError(
                companyName,
                "companyNameError",
                "Company name is required."
            );
        }

        if (industry.value === "") {
            addError(
                industry,
                "industryError",
                "Please select an industry."
            );
        }

        if (address.value.trim().length < 5) {
            addError(
                address,
                "addressError",
                "Please enter the complete company address."
            );
        }

        if (description.value.trim().length < 30) {
            addError(
                description,
                "descriptionError",
                "Description must contain at least 30 characters."
            );
        }

        if (!emailPattern.test(contactEmail.value.trim())) {
            addError(
                contactEmail,
                "contactEmailError",
                "Please enter a valid contact email."
            );
        }

        if (!phonePattern.test(contactNumber.value.trim())) {
            addError(
                contactNumber,
                "contactNumberError",
                "Enter a valid contact number with 8 to 15 digits."
            );
        }

        if (!isValid) {
            event.preventDefault();

            const firstInvalidInput =
                form.querySelector(".input-error");

            if (firstInvalidInput) {
                firstInvalidInput.focus();
            }
        }
    });
});