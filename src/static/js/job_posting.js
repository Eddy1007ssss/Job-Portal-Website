document.addEventListener("DOMContentLoaded", function () {
    const form = document.getElementById("jobPostingForm");

    const jobTitle = document.getElementById("job_title");
    const minimumSalary = document.getElementById("minimum_salary");
    const maximumSalary = document.getElementById("maximum_salary");
    const deadline = document.getElementById("application_deadline");

    const description = document.getElementById("job_description");
    const requirements = document.getElementById("requirements");

    const descriptionCount = document.getElementById("descriptionCount");
    const requirementsCount = document.getElementById("requirementsCount");

    const resetButton = document.getElementById("resetButton");

    let submitAction = "publish";

    document.querySelectorAll('button[type="submit"]').forEach((button) => {
        button.addEventListener("click", function () {
            submitAction = this.value;
        });
    });

    function setMinimumDeadline() {
        const today = new Date();
        const year = today.getFullYear();
        const month = String(today.getMonth() + 1).padStart(2, "0");
        const day = String(today.getDate()).padStart(2, "0");

        deadline.min = `${year}-${month}-${day}`;
    }

    function updateCharacterCount(textarea, counter) {
        counter.textContent = textarea.value.length;
    }

    function showError(input, errorElementId, message) {
        input.classList.add("invalid");
        document.getElementById(errorElementId).textContent = message;
    }

    function clearError(input, errorElementId) {
        input.classList.remove("invalid");
        document.getElementById(errorElementId).textContent = "";
    }

    description.addEventListener("input", function () {
        updateCharacterCount(description, descriptionCount);
        clearError(description, "descriptionError");
    });

    requirements.addEventListener("input", function () {
        updateCharacterCount(requirements, requirementsCount);
        clearError(requirements, "requirementsError");
    });

    jobTitle.addEventListener("input", function () {
        clearError(jobTitle, "jobTitleError");
    });

    deadline.addEventListener("change", function () {
        clearError(deadline, "deadlineError");
    });

    form.addEventListener("submit", function (event) {
        let isValid = true;

        clearError(jobTitle, "jobTitleError");
        clearError(description, "descriptionError");
        clearError(requirements, "requirementsError");
        clearError(deadline, "deadlineError");

        document.getElementById("salaryError").textContent = "";

        if (jobTitle.value.trim().length < 3) {
            showError(
                jobTitle,
                "jobTitleError",
                "Job title must contain at least 3 characters."
            );

            isValid = false;
        }

        /*
        Drafts can contain incomplete descriptions.
        Published jobs must pass all validation.
        */
        if (submitAction === "publish") {
            if (description.value.trim().length < 30) {
                showError(
                    description,
                    "descriptionError",
                    "Job description must contain at least 30 characters."
                );

                isValid = false;
            }

            if (requirements.value.trim().length < 20) {
                showError(
                    requirements,
                    "requirementsError",
                    "Job requirements must contain at least 20 characters."
                );

                isValid = false;
            }

            if (!deadline.value) {
                showError(
                    deadline,
                    "deadlineError",
                    "Please select an application deadline."
                );

                isValid = false;
            }
        }

        const minSalary = Number(minimumSalary.value);
        const maxSalary = Number(maximumSalary.value);

        if (
            minimumSalary.value &&
            maximumSalary.value &&
            maxSalary < minSalary
        ) {
            maximumSalary.classList.add("invalid");

            document.getElementById("salaryError").textContent =
                "Maximum salary cannot be lower than minimum salary.";

            isValid = false;
        } else {
            maximumSalary.classList.remove("invalid");
        }

        if (!isValid) {
            event.preventDefault();

            const firstInvalidField =
                document.querySelector(".invalid");

            if (firstInvalidField) {
                firstInvalidField.scrollIntoView({
                    behavior: "smooth",
                    block: "center"
                });

                firstInvalidField.focus();
            }
        }
    });

    resetButton.addEventListener("click", function () {
        setTimeout(function () {
            descriptionCount.textContent = "0";
            requirementsCount.textContent = "0";

            document
                .querySelectorAll(".invalid")
                .forEach((element) => {
                    element.classList.remove("invalid");
                });

            document
                .querySelectorAll(".error-message")
                .forEach((element) => {
                    element.textContent = "";
                });
        }, 0);
    });

    setMinimumDeadline();
    updateCharacterCount(description, descriptionCount);
    updateCharacterCount(requirements, requirementsCount);
});