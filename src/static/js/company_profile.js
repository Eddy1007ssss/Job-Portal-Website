document.addEventListener("DOMContentLoaded", () => {
    const form = document.getElementById("companyProfileForm");
    const description = document.getElementById("company_description");
    const counter = document.getElementById("descriptionCounter");

    const logoInput = document.getElementById("company_logo");
    const bannerInput = document.getElementById("company_banner");

    const logoPreview = document.getElementById("logoPreview");
    const bannerPreview = document.getElementById("bannerPreview");

    const logoPlaceholder = document.getElementById(
        "logoPreviewPlaceholder"
    );

    const bannerPlaceholder = document.getElementById(
        "bannerPreviewPlaceholder"
    );

    const logoFileName = document.getElementById("logoFileName");
    const bannerFileName = document.getElementById("bannerFileName");

    const allowedImageTypes = [
        "image/png",
        "image/jpeg"
    ];

    const logoMaximumSize = 2 * 1024 * 1024;
    const bannerMaximumSize = 5 * 1024 * 1024;

    if (!form || !description || !counter) {
        return;
    }

    function updateCounter() {
        counter.textContent =
            `${description.value.length} / 1500`;
    }

    function clearFieldError(input, errorId) {
        if (input) {
            input.classList.remove("input-error");
        }

        const errorElement = document.getElementById(errorId);

        if (errorElement) {
            errorElement.textContent = "";
        }
    }

    function addError(input, errorId, message) {
        if (input) {
            input.classList.add("input-error");
        }

        const errorElement = document.getElementById(errorId);

        if (errorElement) {
            errorElement.textContent = message;
        }
    }

    function validateImageFile(
        file,
        maximumSize,
        input,
        errorId,
        imageType
    ) {
        clearFieldError(input, errorId);

        if (!file) {
            return true;
        }

        if (!allowedImageTypes.includes(file.type)) {
            addError(
                input,
                errorId,
                `${imageType} must be a PNG or JPG image.`
            );

            return false;
        }

        if (file.size > maximumSize) {
            const maximumSizeInMB =
                maximumSize / (1024 * 1024);

            addError(
                input,
                errorId,
                `${imageType} must not exceed ` +
                `${maximumSizeInMB} MB.`
            );

            return false;
        }

        return true;
    }

    function displayImagePreview(
        input,
        preview,
        placeholder,
        fileNameElement,
        maximumSize,
        errorId,
        imageType
    ) {
        const file = input.files[0];

        if (!file) {
            fileNameElement.textContent =
                `No new ${imageType.toLowerCase()} selected`;

            return;
        }

        const validFile = validateImageFile(
            file,
            maximumSize,
            input,
            errorId,
            imageType
        );

        if (!validFile) {
            input.value = "";

            fileNameElement.textContent =
                `No new ${imageType.toLowerCase()} selected`;

            return;
        }

        const reader = new FileReader();

        reader.addEventListener("load", () => {
            preview.src = reader.result;
            preview.classList.remove("hidden");

            if (placeholder) {
                placeholder.classList.add("hidden");
            }
        });

        reader.addEventListener("error", () => {
            addError(
                input,
                errorId,
                `Unable to preview the selected ${imageType.toLowerCase()}.`
            );

            input.value = "";
        });

        reader.readAsDataURL(file);
        fileNameElement.textContent = file.name;
    }

    updateCounter();

    description.addEventListener("input", updateCounter);

    if (logoInput) {
        logoInput.addEventListener("change", () => {
            displayImagePreview(
                logoInput,
                logoPreview,
                logoPlaceholder,
                logoFileName,
                logoMaximumSize,
                "companyLogoError",
                "Company logo"
            );
        });
    }

    if (bannerInput) {
        bannerInput.addEventListener("change", () => {
            displayImagePreview(
                bannerInput,
                bannerPreview,
                bannerPlaceholder,
                bannerFileName,
                bannerMaximumSize,
                "companyBannerError",
                "Company banner"
            );
        });
    }

    form.addEventListener("submit", (event) => {
        let isValid = true;

        const companyName =
            document.getElementById("company_name");

        const industry =
            document.getElementById("industry");

        const address =
            document.getElementById("address");

        const contactEmail =
            document.getElementById("contact_email");

        const contactNumber =
            document.getElementById("contact_number");

        const website =
            document.getElementById("website");

        const emailPattern =
            /^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$/;

        const phonePattern =
            /^[0-9+\-\s]{8,15}$/;

        const websitePattern =
            /^https?:\/\/.+/i;

        document
            .querySelectorAll(".field-error")
            .forEach((element) => {
                element.textContent = "";
            });

        document
            .querySelectorAll(
                ".form-group input, " +
                ".form-group select, " +
                ".form-group textarea"
            )
            .forEach((element) => {
                element.classList.remove("input-error");
            });

        if (companyName.value.trim().length < 2) {
            addError(
                companyName,
                "companyNameError",
                "Company name must contain at least 2 characters."
            );

            isValid = false;
        }

        if (industry.value === "") {
            addError(
                industry,
                "industryError",
                "Please select an industry."
            );

            isValid = false;
        }

        if (address.value.trim().length < 5) {
            addError(
                address,
                "addressError",
                "Please enter the complete company address."
            );

            isValid = false;
        }

        if (description.value.trim().length < 30) {
            addError(
                description,
                "descriptionError",
                "Description must contain at least 30 characters."
            );

            isValid = false;
        }

        if (description.value.length > 1500) {
            addError(
                description,
                "descriptionError",
                "Description must not exceed 1500 characters."
            );

            isValid = false;
        }

        if (!emailPattern.test(contactEmail.value.trim())) {
            addError(
                contactEmail,
                "contactEmailError",
                "Please enter a valid contact email."
            );

            isValid = false;
        }

        if (!phonePattern.test(contactNumber.value.trim())) {
            addError(
                contactNumber,
                "contactNumberError",
                "Enter a valid contact number with 8 to 15 characters."
            );

            isValid = false;
        }

        if (
            website &&
            website.value.trim() !== "" &&
            !websitePattern.test(website.value.trim())
        ) {
            addError(
                website,
                "websiteError",
                "Website must begin with http:// or https://."
            );

            isValid = false;
        }

        if (
            logoInput &&
            logoInput.files.length > 0
        ) {
            const logoIsValid = validateImageFile(
                logoInput.files[0],
                logoMaximumSize,
                logoInput,
                "companyLogoError",
                "Company logo"
            );

            if (!logoIsValid) {
                isValid = false;
            }
        }

        if (
            bannerInput &&
            bannerInput.files.length > 0
        ) {
            const bannerIsValid = validateImageFile(
                bannerInput.files[0],
                bannerMaximumSize,
                bannerInput,
                "companyBannerError",
                "Company banner"
            );

            if (!bannerIsValid) {
                isValid = false;
            }
        }

        if (!isValid) {
            event.preventDefault();

            const firstInvalidInput =
                form.querySelector(".input-error");

            if (firstInvalidInput) {
                firstInvalidInput.focus();

                firstInvalidInput.scrollIntoView({
                    behavior: "smooth",
                    block: "center"
                });
            }
        }
    });
});