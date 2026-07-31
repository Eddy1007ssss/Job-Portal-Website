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
