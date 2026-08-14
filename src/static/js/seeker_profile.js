document.addEventListener("DOMContentLoaded", () => {
    const sidebar = document.getElementById("sidebar");
    const overlay = document.getElementById("sidebarOverlay");
    const mobileButton = document.getElementById("mobileMenuButton");
    const profileButton = document.getElementById("profileMenuButton");
    const profileDropdown = document.getElementById("profileDropdown");
    const imageInput = document.getElementById("profileImageInput");
    const imageForm = document.getElementById("profileImageForm");
    const resumeInput = document.getElementById("resumeInput");
    const selectedResumeName =
        document.getElementById("selectedResumeName");
    const currentlyWorking =
        document.getElementById("currentlyWorking");
    const experienceEndDate =
        document.getElementById("experienceEndDate");
    const educationModal = document.getElementById("educationModal");
    const educationForm = document.getElementById("educationForm");
    const educationQualification =
        document.getElementById("educationQualification");
    const educationInstitution =
        document.getElementById("educationInstitution");
    const educationFieldOfStudy =
        document.getElementById("educationFieldOfStudy");
    const educationStartYear =
        document.getElementById("educationStartYear");
    const educationEndYear =
        document.getElementById("educationEndYear");
    const educationEndYearLabel =
        document.getElementById("educationEndYearLabel");
    const educationStatus = document.getElementById("educationStatus");
    const educationCertificateGroup =
        document.getElementById("educationCertificateGroup");
    const educationCertificateFile =
        document.getElementById("educationCertificateFile");
    const educationCurrentCertificate =
        document.getElementById("educationCurrentCertificate");
    const educationSubmitButton =
        document.getElementById("educationSubmitButton");
    const skillModal = document.getElementById("skillModal");
    const skillForm = document.getElementById("skillForm");
    const skillName = document.getElementById("skillName");
    const skillSubmitButton = document.getElementById("skillSubmitButton");
    const certificateModal = document.getElementById("certificateModal");
    const certificateForm = document.getElementById("certificateForm");
    const certificateName = document.getElementById("certificateName");
    const certificateIssuer = document.getElementById("certificateIssuer");
    const certificateIssueDate =
        document.getElementById("certificateIssueDate");
    const certificateFile = document.getElementById("certificateFile");
    const certificateCurrentFile =
        document.getElementById("certificateCurrentFile");
    const certificateRemoveFileGroup =
        document.getElementById("certificateRemoveFileGroup");
    const certificateRemoveFile =
        document.getElementById("certificateRemoveFile");
    const certificateSubmitButton =
        document.getElementById("certificateSubmitButton");
    const currentYear = new Date().getFullYear();
    const currentDate = new Date();
    const currentMonth = [
        currentDate.getFullYear(),
        String(currentDate.getMonth() + 1).padStart(2, "0"),
    ].join("-");

    function closeSidebar() {
        sidebar?.classList.remove("open");
        overlay?.classList.remove("show");
        mobileButton?.setAttribute("aria-expanded", "false");
    }

    mobileButton?.addEventListener("click", () => {
        sidebar?.classList.add("open");
        overlay?.classList.add("show");
        mobileButton.setAttribute("aria-expanded", "true");
    });

    overlay?.addEventListener("click", closeSidebar);

    profileButton?.addEventListener("click", (event) => {
        event.stopPropagation();
        const isOpen = profileDropdown?.classList.toggle("show");
        profileButton.setAttribute("aria-expanded", String(Boolean(isOpen)));
    });

    document.addEventListener("click", (event) => {
        if (
            profileDropdown &&
            profileButton &&
            !profileDropdown.contains(event.target) &&
            !profileButton.contains(event.target)
        ) {
            profileDropdown.classList.remove("show");
            profileButton.setAttribute("aria-expanded", "false");
        }
    });

    document
        .querySelectorAll("[data-open-modal]")
        .forEach((button) => {
            button.addEventListener("click", () => {
                const modal = document.getElementById(
                    button.dataset.openModal
                );

                modal?.classList.add("show");
                document.body.classList.add("modal-open");
            });
        });

    document
        .querySelectorAll("[data-close-modal]")
        .forEach((button) => {
            button.addEventListener("click", () => {
                const modal = document.getElementById(
                    button.dataset.closeModal
                );

                modal?.classList.remove("show");
                document.body.classList.remove("modal-open");
            });
        });

    document
        .querySelectorAll(".modal-overlay")
        .forEach((modal) => {
            modal.addEventListener("click", (event) => {
                if (event.target === modal) {
                    modal.classList.remove("show");
                    document.body.classList.remove("modal-open");
                }
            });
        });

    imageInput?.addEventListener("change", () => {
        const file = imageInput.files?.[0];

        if (!file) {
            return;
        }

        const validTypes = [
            "image/png",
            "image/jpeg",
            "image/webp",
        ];

        if (!validTypes.includes(file.type)) {
            alert("Please select a PNG, JPG, JPEG or WEBP image.");
            imageInput.value = "";
            return;
        }

        imageForm?.submit();
    });

    resumeInput?.addEventListener("change", () => {
        const file = resumeInput.files?.[0];

        if (!file) {
            selectedResumeName.textContent = "";
            return;
        }

        const extension = file.name
            .split(".")
            .pop()
            ?.toLowerCase();

        if (
            extension !== "pdf" ||
            file.type !== "application/pdf"
        ) {
            alert("Please select a valid PDF file.");
            resumeInput.value = "";
            selectedResumeName.textContent = "";
            return;
        }

        selectedResumeName.textContent =
            `Selected: ${file.name}. Uploading...`;

        resumeInput.form?.submit();
    });

    currentlyWorking?.addEventListener("change", () => {
        if (!experienceEndDate) {
            return;
        }

        experienceEndDate.disabled = currentlyWorking.checked;

        if (currentlyWorking.checked) {
            experienceEndDate.value = "";
        }
    });

    function updateEducationStatusFields() {
        if (
            !educationStatus ||
            !educationCertificateGroup ||
            !educationCertificateFile ||
            !educationEndYear ||
            !educationEndYearLabel
        ) {
            return;
        }

        const isCompleted = educationStatus.value === "Completed";
        educationCertificateGroup.hidden = !isCompleted;
        educationCertificateFile.disabled = !isCompleted;
        educationEndYearLabel.textContent = isCompleted
            ? "Graduation Year"
            : "Expected Graduation Year";
        educationEndYear.max = isCompleted ? String(currentYear) : "";

        if (!isCompleted) {
            educationCertificateFile.value = "";
        }

        if (educationCurrentCertificate) {
            const certificateName =
                educationCurrentCertificate.dataset.filename || "";
            educationCurrentCertificate.hidden =
                !isCompleted || !certificateName;
            educationCurrentCertificate.textContent = certificateName
                ? `Current certificate: ${certificateName}`
                : "";
        }
    }

    function setEducationModalHeading(title, description) {
        const heading = educationModal?.querySelector(".modal-header h2");
        const subtitle = educationModal?.querySelector(".modal-header p");

        if (heading) {
            heading.textContent = title;
        }

        if (subtitle) {
            subtitle.textContent = description;
        }
    }

    function prepareEducationAddForm() {
        if (!educationForm || !educationStatus) {
            return;
        }

        educationForm.reset();
        educationForm.action = educationForm.dataset.addUrl || "";
        educationStatus.value = "Completed";

        if (educationCurrentCertificate) {
            educationCurrentCertificate.dataset.filename = "";
        }

        if (educationSubmitButton) {
            educationSubmitButton.textContent = "Add Education";
        }

        setEducationModalHeading(
            "Add Education",
            "Add an education record."
        );
        updateEducationStatusFields();
    }

    function prepareEducationEditForm(button) {
        if (
            !educationForm ||
            !educationQualification ||
            !educationInstitution ||
            !educationFieldOfStudy ||
            !educationStartYear ||
            !educationEndYear ||
            !educationStatus
        ) {
            return;
        }

        educationForm.reset();
        educationForm.action = button.dataset.updateUrl || "";
        educationQualification.value = button.dataset.qualification || "";
        educationInstitution.value = button.dataset.institution || "";
        educationFieldOfStudy.value = button.dataset.fieldOfStudy || "";
        educationStartYear.value = button.dataset.startYear || "";
        educationEndYear.value = button.dataset.endYear || "";
        educationStatus.value = button.dataset.status || "Completed";

        if (educationCurrentCertificate) {
            educationCurrentCertificate.dataset.filename =
                button.dataset.certificateName || "";
        }

        if (educationSubmitButton) {
            educationSubmitButton.textContent = "Update Education";
        }

        setEducationModalHeading(
            "Edit Education",
            "Update this education record."
        );
        updateEducationStatusFields();
    }

    educationStartYear?.setAttribute("max", String(currentYear));
    educationStatus?.addEventListener(
        "change",
        updateEducationStatusFields
    );

    educationCertificateFile?.addEventListener("change", () => {
        const file = educationCertificateFile.files?.[0];

        if (!file) {
            return;
        }

        const extension = file.name.split(".").pop()?.toLowerCase();
        const allowedExtensions = ["pdf", "png", "jpg", "jpeg"];

        if (!extension || !allowedExtensions.includes(extension)) {
            alert("Certificate must be a PDF, PNG, JPG or JPEG file.");
            educationCertificateFile.value = "";
            return;
        }

        if (file.size > 5 * 1024 * 1024) {
            alert("Certificate file must not exceed 5 MB.");
            educationCertificateFile.value = "";
        }
    });

    document
        .querySelectorAll("[data-education-mode='add']")
        .forEach((button) => {
            button.addEventListener("click", prepareEducationAddForm);
        });

    document
        .querySelectorAll(".education-edit-button")
        .forEach((button) => {
            button.addEventListener("click", () => {
                prepareEducationEditForm(button);
            });
        });

    educationForm?.addEventListener("submit", (event) => {
        if (!educationStartYear || !educationEndYear || !educationStatus) {
            return;
        }

        const startYear = Number(educationStartYear.value);
        const endYear = Number(educationEndYear.value);
        let validationMessage = "";

        if (endYear < startYear) {
            validationMessage =
                "End year cannot be earlier than start year.";
        } else if (
            educationStatus.value === "Completed" &&
            endYear > currentYear
        ) {
            validationMessage =
                "A completed education end year cannot be in the future.";
        }

        educationEndYear.setCustomValidity(validationMessage);

        if (validationMessage) {
            event.preventDefault();
            educationEndYear.reportValidity();
        }
    });

    educationEndYear?.addEventListener("input", () => {
        educationEndYear.setCustomValidity("");
    });

    updateEducationStatusFields();

    function setCredentialModalHeading(modal, title, description) {
        const heading = modal?.querySelector(".modal-header h2");
        const subtitle = modal?.querySelector(".modal-header p");

        if (heading) {
            heading.textContent = title;
        }

        if (subtitle) {
            subtitle.textContent = description;
        }
    }

    function prepareSkillAddForm() {
        if (!skillForm) {
            return;
        }

        skillForm.reset();
        skillForm.action = skillForm.dataset.addUrl || "";

        if (skillSubmitButton) {
            skillSubmitButton.textContent = "Add Skill";
        }

        setCredentialModalHeading(
            skillModal,
            "Add Skill",
            "Add one skill."
        );
    }

    function prepareSkillEditForm(button) {
        if (!skillForm || !skillName) {
            return;
        }

        skillForm.reset();
        skillForm.action = button.dataset.updateUrl || "";
        skillName.value = button.dataset.skillName || "";

        if (skillSubmitButton) {
            skillSubmitButton.textContent = "Update Skill";
        }

        setCredentialModalHeading(
            skillModal,
            "Edit Skill",
            "Update this skill."
        );
    }

    function showCurrentCertificateFile(filename) {
        if (
            !certificateCurrentFile ||
            !certificateRemoveFileGroup ||
            !certificateRemoveFile
        ) {
            return;
        }

        certificateCurrentFile.hidden = !filename;
        certificateCurrentFile.textContent = filename
            ? `Current file: ${filename}`
            : "";
        certificateRemoveFileGroup.hidden = !filename;
        certificateRemoveFile.checked = false;
    }

    function prepareCertificateAddForm() {
        if (!certificateForm) {
            return;
        }

        certificateForm.reset();
        certificateForm.action = certificateForm.dataset.addUrl || "";
        showCurrentCertificateFile("");

        if (certificateSubmitButton) {
            certificateSubmitButton.textContent = "Add Certificate";
        }

        setCredentialModalHeading(
            certificateModal,
            "Add Certificate",
            "Add a professional certificate."
        );
    }

    function prepareCertificateEditForm(button) {
        if (
            !certificateForm ||
            !certificateName ||
            !certificateIssuer ||
            !certificateIssueDate
        ) {
            return;
        }

        certificateForm.reset();
        certificateForm.action = button.dataset.updateUrl || "";
        certificateName.value = button.dataset.certificateName || "";
        certificateIssuer.value = button.dataset.issuer || "";
        certificateIssueDate.value = button.dataset.issueDate || "";
        showCurrentCertificateFile(
            button.dataset.originalFilename || ""
        );

        if (certificateSubmitButton) {
            certificateSubmitButton.textContent = "Update Certificate";
        }

        setCredentialModalHeading(
            certificateModal,
            "Edit Certificate",
            "Update this certificate."
        );
    }

    document
        .querySelectorAll("[data-skill-mode='add']")
        .forEach((button) => {
            button.addEventListener("click", prepareSkillAddForm);
        });

    document
        .querySelectorAll(".skill-edit-button")
        .forEach((button) => {
            button.addEventListener("click", () => {
                prepareSkillEditForm(button);
            });
        });

    certificateIssueDate?.setAttribute("max", currentMonth);

    document
        .querySelectorAll("[data-certificate-mode='add']")
        .forEach((button) => {
            button.addEventListener("click", prepareCertificateAddForm);
        });

    document
        .querySelectorAll(".certificate-edit-button")
        .forEach((button) => {
            button.addEventListener("click", () => {
                prepareCertificateEditForm(button);
            });
        });

    certificateFile?.addEventListener("change", () => {
        const file = certificateFile.files?.[0];

        if (!file) {
            return;
        }

        const extension = file.name.split(".").pop()?.toLowerCase();
        const allowedExtensions = [
            "pdf",
            "png",
            "jpg",
            "jpeg",
            "doc",
            "docx",
        ];

        if (!extension || !allowedExtensions.includes(extension)) {
            alert("Certificate must be PDF, PNG, JPG, DOC or DOCX.");
            certificateFile.value = "";
            return;
        }

        if (file.size > 5 * 1024 * 1024) {
            alert("Certificate file must not exceed 5 MB.");
            certificateFile.value = "";
            return;
        }

        if (certificateRemoveFile) {
            certificateRemoveFile.checked = false;
        }
    });

    document
        .querySelectorAll(".flash-message")
        .forEach((message) => {
            window.setTimeout(() => {
                message.classList.add("hide");

                window.setTimeout(() => {
                    message.remove();
                }, 300);
            }, 3000);
        });

    document.addEventListener("keydown", (event) => {
        if (event.key !== "Escape") {
            return;
        }

        closeSidebar();
        profileDropdown?.classList.remove("show");

        document
            .querySelectorAll(".modal-overlay.show")
            .forEach((modal) => modal.classList.remove("show"));

        document.body.classList.remove("modal-open");
    });
});
