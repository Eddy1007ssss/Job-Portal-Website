document.addEventListener("DOMContentLoaded", () => {
    const mobileMenuButton = document.getElementById("mobileMenuButton");
    const sidebar = document.getElementById("sidebar");
    const sidebarOverlay = document.getElementById("sidebarOverlay");

    const profileMenuButton = document.getElementById("profileMenuButton");
    const profileDropdown = document.getElementById("profileDropdown");
    const profileMenu = profileMenuButton?.closest(".profile-menu");

    const editProfileButton = document.getElementById("editProfileButton");
    const profileModal = document.getElementById("profileModal");
    const profileForm = document.getElementById("profileForm");

    const profileImageInput =
        document.getElementById("profileImageInput");

    const profilePicture =
        document.getElementById("profilePicture");

    const resumeInput =
        document.getElementById("resumeInput");

    const selectedResumeName =
        document.getElementById("selectedResumeName");

    const toastMessage =
        document.getElementById("toastMessage");

    function openSidebar() {
        sidebar?.classList.add("open");
        sidebarOverlay?.classList.add("show");
        document.body.style.overflow = "hidden";
    }

    function closeSidebar() {
        sidebar?.classList.remove("open");
        sidebarOverlay?.classList.remove("show");
        document.body.style.overflow = "";
    }

    mobileMenuButton?.addEventListener("click", () => {
        if (sidebar?.classList.contains("open")) {
            closeSidebar();
        } else {
            openSidebar();
        }
    });

    sidebarOverlay?.addEventListener("click", closeSidebar);

    document.querySelectorAll(".sidebar-item").forEach((sidebarItem) => {
        sidebarItem.addEventListener("click", () => {
            if (window.innerWidth <= 960) {
                closeSidebar();
            }
        });
    });

    profileMenuButton?.addEventListener("click", (event) => {
        event.stopPropagation();

        profileDropdown?.classList.toggle("show");
        profileMenu?.classList.toggle("open");
    });

    document.addEventListener("click", (event) => {
        if (!profileMenu?.contains(event.target)) {
            profileDropdown?.classList.remove("show");
            profileMenu?.classList.remove("open");
        }
    });

    function openModal(modalElement) {
        if (!modalElement) {
            return;
        }

        modalElement.classList.add("show");
        document.body.style.overflow = "hidden";
    }

    function closeModal(modalElement) {
        if (!modalElement) {
            return;
        }

        modalElement.classList.remove("show");
        document.body.style.overflow = "";
    }

    editProfileButton?.addEventListener("click", () => {
        openModal(profileModal);
    });

    document.querySelectorAll("[data-modal]").forEach((button) => {
        button.addEventListener("click", () => {
            const modalId = button.dataset.modal;
            const modal = document.getElementById(modalId);

            openModal(modal);
        });
    });

    document
        .querySelectorAll("[data-close-modal]")
        .forEach((button) => {
            button.addEventListener("click", () => {
                const modalId = button.dataset.closeModal;
                const modal = document.getElementById(modalId);

                closeModal(modal);
            });
        });

    profileModal?.addEventListener("click", (event) => {
        if (event.target === profileModal) {
            closeModal(profileModal);
        }
    });

    document.addEventListener("keydown", (event) => {
        if (event.key === "Escape") {
            closeModal(profileModal);
            closeSidebar();

            profileDropdown?.classList.remove("show");
            profileMenu?.classList.remove("open");
        }
    });

    profileImageInput?.addEventListener("change", () => {
        const selectedFile = profileImageInput.files[0];

        if (!selectedFile) {
            return;
        }

        if (!selectedFile.type.startsWith("image/")) {
            alert("Please select a valid image file.");
            profileImageInput.value = "";
            return;
        }

        const reader = new FileReader();

        reader.onload = (event) => {
            profilePicture.src = event.target.result;
            showToast("Profile picture updated.");
        };

        reader.readAsDataURL(selectedFile);
    });

    resumeInput?.addEventListener("change", () => {
        const selectedFile = resumeInput.files[0];

        if (!selectedFile) {
            selectedResumeName.textContent = "";
            return;
        }

        const maximumSize = 5 * 1024 * 1024;

        if (selectedFile.size > maximumSize) {
            alert("The resume file must be smaller than 5 MB.");
            resumeInput.value = "";
            selectedResumeName.textContent = "";
            return;
        }

        selectedResumeName.textContent =
            `Selected file: ${selectedFile.name}`;

        showToast("Resume selected successfully.");
    });

    profileForm?.addEventListener("submit", (event) => {
        event.preventDefault();

        const fullName =
            document.getElementById("fullName").value.trim();

        const jobTitle =
            document.getElementById("jobTitle").value.trim();

        const email =
            document.getElementById("email").value.trim();

        const phone =
            document.getElementById("phone").value.trim();

        const location =
            document.getElementById("location").value.trim();

        const aboutMe =
            document.getElementById("aboutMe").value.trim();

        const nameHeading =
            document.querySelector(".profile-name-row h2");

        const titleHeading =
            document.querySelector(".profile-information h3");

        const contactParagraphs =
            document.querySelectorAll(".contact-information p");

        const aboutDescription =
            document.querySelector(".about-description");

        if (nameHeading) {
            nameHeading.textContent = fullName;
        }

        if (titleHeading) {
            titleHeading.textContent = jobTitle;
        }

        if (contactParagraphs.length >= 3) {
            contactParagraphs[0].innerHTML =
                `<i class="fa-solid fa-location-dot"></i>${escapeHTML(location)}`;

            contactParagraphs[1].innerHTML =
                `<i class="fa-regular fa-envelope"></i>${escapeHTML(email)}`;

            contactParagraphs[2].innerHTML =
                `<i class="fa-solid fa-phone"></i>${escapeHTML(phone)}`;
        }

        if (aboutDescription) {
            aboutDescription.textContent = aboutMe;
        }

        const profileMenuName =
            document.querySelector(".profile-menu-name");

        if (profileMenuName) {
            profileMenuName.textContent = fullName;
        }

        closeModal(profileModal);
        showToast("Profile updated successfully.");
    });

    function showToast(message) {
        if (!toastMessage) {
            return;
        }

        const messageElement =
            toastMessage.querySelector("span");

        if (messageElement) {
            messageElement.textContent = message;
        }

        toastMessage.classList.add("show");

        window.clearTimeout(window.profileToastTimer);

        window.profileToastTimer = window.setTimeout(() => {
            toastMessage.classList.remove("show");
        }, 3000);
    }

    function escapeHTML(value) {
        const temporaryElement = document.createElement("div");
        temporaryElement.textContent = value;
        return temporaryElement.innerHTML;
    }
});